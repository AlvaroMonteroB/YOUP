import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Any, Dict
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import requests

# 1. Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
LOG_FILE_PATH = "logs/app.log"
#main bot
MAIN_TOKEN=os.getenv("MAIN_TOKEN")
MAIN_AGENTID=os.getenv("MAIN_AGENTID")
#Bot de summary
SUMM_TOKEN=os.getenv("SUMM_TOKEN")
SUMM_AGENTID=os.getenv("SUMM_AGENTID")
# --- CONFIGURACIÓN DE LOGS ---
if not os.path.exists("logs"):
    os.makedirs("logs")

logger = logging.getLogger("marketing_agent")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(LOG_FILE_PATH, when="midnight", interval=1, backupCount=7)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# -----------------------------

app = FastAPI(title="Marketing Agent Tool API")

# 2. Configuración de Base de Datos
client = AsyncIOMotorClient(MONGO_URI)
db = client.marketing_db
users_collection = db.users

# 3. Modelos de Datos

class UserProfile(BaseModel):
    function_call_username: str = Field(..., description="Identificador o teléfono del usuario (puede incluir prefijos con --)")
    #preferences: str = Field(..., description="Texto libre con preferencias o resumen")
    source: Optional[str] = Field("bot_marketing", description="Origen del lead")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentResponse(BaseModel):
    """Modelo para documentación en OpenAPI (Swagger)"""
    raw: Dict[str, Any]
    markdown: str
    type: str
    desc: str

# 4. Helper de Respuesta (Tu nuevo método)
def responder(status_code: int, title: str, raw_data: Dict[str, Any]):
    """
    Estandariza la respuesta según tus requerimientos:
    - Inyecta 'status': 'exito'/'error' en raw.
    - Genera markdown y desc combinando title y mensaje.
    - Retorna JSONResponse.
    """
    # Buscamos el mensaje en las claves comunes o usamos un default
    mensaje = raw_data.get("mensaje") or raw_data.get("msgRetorno") or "Operación completada."
    
    # Determinamos status basado en el código HTTP
    status_str = "error" if status_code >= 400 else "exito"
    
    return JSONResponse(status_code=status_code, content={
        "raw": {"status": status_str, **raw_data},
        "markdown": f"**{title}**\n\n{mensaje}",
        "type": "markdown",
        "desc": f"{mensaje}\n\n"
    })

async def get_chat(telefono_objetivo):
    """
    Obtiene el historial del MAIN BOT (donde ocurre la conversación).
    """
    # Credenciales del MAIN BOT
    MAIN_AGENTID = os.getenv("MAIN_AGENTID")
    MAIN_TOKEN = os.getenv("MAIN_TOKEN")
    AS_ACCOUNT = os.getenv("AS_ACCOUNT")
    
    url_list = 'https://agents.dyna.ai/openapi/v1/conversation/segment/get_list/'
    
    headers = {
        'Content-Type': 'application/json',
        'cybertron-robot-key': MAIN_AGENTID,
        'cybertron-robot-token': MAIN_TOKEN
    }
    #logger.info(f"{MAIN_AGENTID} , {MAIN_TOKEN}")
     
    # 1. Buscar la conversación en la lista
    payload_list = {
        "username": AS_ACCOUNT.strip(),
        "filter_mode": 0,
         "filter_user_code": "",
        "create_start_time": "",
        "create_end_time": "",
        "message_source": "",
        "page": 1,
        "pagesize": 20 
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp_list = await client.post(url_list, headers=headers, json=payload_list)
            data = resp_list.json()
            logger.info(resp_list.history)
            
            if data.get("code") != "000000":
                logger.error(f"Error buscando chat: {data.get('message')}")
                return None

            # Filtrar por teléfono dentro del user_code
            segment_code = None
            for item in data.get("data", {}).get("list", []):
                if telefono_objetivo in item.get("user_code", ""):
                    segment_code = item.get("segment_code")
                    break
            
            if not segment_code:
                return None

            # 2. Obtener el detalle (los mensajes)
            url_detail = 'https://agents.dyna.ai/openapi/v1/conversation/segment/detail_list/'

            # 1. Headers exactos del curl (Copiados tal cual)
            headers = {
                'Content-Type': 'application/json',
                'cybertron-robot-key': MAIN_AGENTID,
                'cybertron-robot-token': MAIN_TOKEN
            }

            # 2. Payload completo coincidiendo con el --data-raw
            # Nota: Agregué los campos vacíos que faltaban y ajusté el pagesize a 20 como el curl
            payload_detail = {
                "username": AS_ACCOUNT, # Asegúrate de que esta variable sea "juan.calderon@dyna.ai"
                "segment_code": segment_code,
                "create_start_time": "",
                "create_end_time": "",
                "message_source": "",
                "question": "",
                "page": 1,
                "pagesize": 20 
            }

            # 3. Petición
            resp_detail = await client.post(url_detail, headers=headers, json=payload_detail)
            return resp_detail.json()

        except Exception as e:
            logger.error(f"Error en get_chat: {e}")
            return None

async def summarize(conversation):
    """
    Envía un texto (conversation) a la API del agente para obtener un resumen.
    """
    
    # 1. Validar que tengamos datos para enviar
    if not conversation:
        logger.warning("Intento de resumir una conversación vacía.")
        return "No hay datos para resumir."

    # 2. Obtener credenciales (se cargan al inicio con load_dotenv)
    AGENT_API_URL = os.getenv("AGENT_API_URL")
    AGENT_KEY = SUMM_AGENTID
    AGENT_TOKEN = SUMM_TOKEN
    AS_ACCOUNT = os.getenv("AS_ACCOUNT")

    # 3. Preparar la petición
    headers = {
        'Content-Type': 'application/json',
        'cybertron-robot-key': AGENT_KEY,
        'cybertron-robot-token': AGENT_TOKEN
    }

    payload = {
        "username": AS_ACCOUNT,
        "question": conversation  # Aquí va el texto/prompt construido
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 4. Llamada a la API con httpx (asíncrono)
            response = await client.post(AGENT_API_URL, headers=headers, json=payload)
            
            # Verificar códigos de error (4xx, 5xx)
            response.raise_for_status()

            # 5. Procesar respuesta
            data = response.json()
            
            # Extraer la respuesta de forma segura
            answer = data.get("data", {}).get("answer")
            
            if answer:
                return answer
            else:
                logger.warning(f"La API respondió OK pero sin respuesta: {data}")
                return "No se pudo generar el resumen."

    except httpx.TimeoutException:
        logger.error("Timeout al conectar con el agente de resúmenes.")
        return "El servicio de resumen tardó demasiado en responder."
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP al resumir: {e}")
        return f"Error de la API de resumen: {e.response.status_code}"
        
    except Exception as e:
        logger.error(f"Error inesperado en summarize: {e}")
        return "Ocurrió un error interno al procesar el resumen."

# 5. Endpoints

@app.post("/save-lead", response_model=AgentResponse)
async def save_lead(user: UserProfile):
    logger.info(f"Save lead: {user}")
    """
    Guarda información extrayendo el teléfono limpio.
    """
    try:
        # Lógica de extracción de teléfono
        full_username = user.function_call_username
        raw_phone = full_username.split("--")[-1] if "--" in full_username else full_username
        
        user_dict = user.model_dump()
        user_dict["phone_number"] = raw_phone

        logger.info(f"Intentando guardar/actualizar lead: {raw_phone}")

        # Upsert en Mongo
        result = await users_collection.update_one(
            {"phone_number": raw_phone},
            {"$set": user_dict},
            upsert=True
        )

        logger.info(f"Lead procesado: {raw_phone}")

        if result.upserted_id:
            # Preparamos datos para responder()
            raw_data = {
                "id": str(result.upserted_id),
                "action": "created",
                "phone": raw_phone,
                "mensaje": f"¡Hola! ¿En qué podemos ayudarle hoy?\n Estamos aquí para darte cualquier información a cerca de los productos que ofrecemos"
            }
            return responder(201, " ", raw_data)
        else:
            raw_data = {
                "id": raw_phone,
                "action": "updated",
                "phone": raw_phone,
                "mensaje": f"¡Hola de nuevo! Seguimos motivados para poder ayudarle, si tiene alguna duda, ¡no dude en preguntar!"
            }
            return responder(200, "Actualización Exitosa", raw_data)

    except Exception as e:
        logger.error(f"Error DB save_lead: {str(e)}")
        # Usamos responder para devolver el error formateado
        return responder(500, "Error Interno", {"mensaje": f"Error al guardar datos: {str(e)}"})


@app.get("/get-lead/{phone_number}")
async def get_lead(phone_number: str):
    """
    Busca usuario y retorna formato estandarizado usando responder().
    """
    logger.info(f"Buscando lead: {phone_number}")
    
    user = await users_collection.find_one(
        {"phone_number": phone_number},
        {"_id": 0}
    )
    
    if user:
        if "created_at" in user and isinstance(user["created_at"], datetime):
            user["created_at"] = user["created_at"].isoformat()

        logger.info(f"Lead encontrado: {phone_number}")
        
        # Agregamos 'mensaje' al dict del usuario para que responder() lo use
        user["mensaje"] = f"Información encontrada. Intereses: {user.get('preferences', 'Sin datos')}"
        
        return responder(200, "Usuario Encontrado", user)
    else:
        logger.warning(f"Lead no encontrado: {phone_number}")
        
        raw_data = {
            "found": False, 
            "phone": phone_number, 
            "mensaje": f"No encontré registros previos para el número {phone_number}."
        }
        # Retornamos 200 (éxito en la consulta) pero indicando que no se encontró en el mensaje
        # Si prefieres que sea un error http, cambia 200 por 404
        return responder(200, "Usuario No Encontrado", raw_data)


@app.post("/get-logs")
async def get_system_logs():
    """
    Endpoint POST para descargar/ver los logs del sistema.
    """
    try:
        if os.path.exists(LOG_FILE_PATH):
            logger.info("Acceso a descarga de logs solicitado.")
            return FileResponse(
                path=LOG_FILE_PATH, 
                filename="system_logs.txt", 
                media_type="text/plain"
            )
        else:
            return responder(404, "Logs No Disponibles", {
                "error": "no_logs",
                "mensaje": "No hay archivo de logs disponible actualmente."
            })
    except Exception as e:
        logger.error(f"Error al leer logs: {e}")
        return responder(500, "Error de Sistema", {"mensaje": "Error crítico leyendo logs."})


@app.get("/generate_summary_batch")
async def generate_summary_batch():
    """
    Recorre la base de datos, busca usuarios con teléfono,
    descarga sus chats y actualiza sus resúmenes masivamente.
    """
    logger.info("Iniciando generación masiva de resúmenes...")
    
    processed_count = 0
    skipped_count = 0
    
    # Iteramos asíncronamente sobre todos los usuarios que tengan el campo phone_number
    async for user_doc in users_collection.find({"phone_number": {"$exists": True}}):
        phone = user_doc.get("phone_number")
        
        try:
            # 1. Obtener Chat del Main Bot
            # Si no hay chat reciente, saltamos al siguiente usuario
            logger.info(f"Obteniendo chat {phone}")
            chat_info = await get_chat(phone)
            if not chat_info:
                logger.info(f"Sin historial de chat para: {phone}")
                skipped_count += 1
                continue

            # 2. Generar Resumen con el Summary Bot
            logger.info(f"Obteniendo generando resumen {phone}")
            summary_text = await summarize(chat_info)

            # 3. Actualizar en Base de Datos
            await users_collection.update_one(
                {"_id": user_doc["_id"]},
                {
                    "$set": {
                        "summary": summary_text,
                        "last_summary_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Resumen actualizado para: {phone}")
            processed_count += 1

        except Exception as e:
            # Capturamos el error para que no detenga el bucle completo, solo este usuario
            logger.error(f"Error procesando usuario {phone}: {e}")
            skipped_count += 1
            continue

    # Retornamos el reporte final
    raw_data = {
        "processed": processed_count,
        "skipped_or_failed": skipped_count,
        "mensaje": f"Proceso finalizado. Se actualizaron {processed_count} usuarios."
    }
    
    return responder(200, "Resumen Masivo Completado", raw_data)
            

@app.get("/")
async def health_check():
    return {"status": "online", "service": "Marketing Agent Database Tool"}