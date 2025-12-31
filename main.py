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
import json

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
    # --- CARGA DE CREDENCIALES ---
    MAIN_AGENTID = os.getenv("MAIN_AGENTID", "").strip()
    MAIN_TOKEN = os.getenv("MAIN_TOKEN", "").strip()
    AS_ACCOUNT = os.getenv("AS_ACCOUNT", "").strip()
    
    headers = {
        'Content-Type': 'application/json',
        'cybertron-robot-key': MAIN_AGENTID,
        'cybertron-robot-token': MAIN_TOKEN
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # ==========================================
        # PASO 1: GET LIST (ESTA PARTE YA FUNCIONA)
        # ==========================================
        url_list = 'https://agents.dyna.ai/openapi/v1/conversation/segment/get_list/'
        payload_list = {
            "username": AS_ACCOUNT,
            "filter_mode": 0,
            "filter_user_code": "", 
            "page": 1,
            "pagesize": 20 
        }

        try:
            resp_list = await client.post(url_list, headers=headers, json=payload_list)
            data_list = resp_list.json()
            
            # Verificación rápida
            if data_list.get("code") != "000000":
                logger.error(f"Error en Lista: {data_list}")
                return []

            lista_chats = data_list.get("data", {}).get("list", [])
            logger.info(f"Chats encontrados: {len(lista_chats)}")

            # ==========================================
            # PASO INTERMEDIO: ENCONTRAR EL SEGMENT_CODE
            # ==========================================
            segment_code = None
            
            # Limpiamos el teléfono objetivo para asegurar el match
            phone_clean = telefono_objetivo.replace(" ", "").replace("+", "") 

            print(f"--- BUSCANDO: {phone_clean} ---")
            
            for item in lista_chats:
                user_code = item.get("user_code", "")
                
                # Buscamos si el teléfono limpio está dentro del user_code
                if phone_clean in user_code:
                    segment_code = item.get("segment_code")
                    # IMPRIMIR PARA DEPURAR: ¿Cuál estamos agarrando?
                    print(f"✅ MATCH: User: {user_code} | Segment: {segment_code}")
                    break # <--- OJO: Esto agarra solo el PRIMER chat encontrado.
            
            if not segment_code:
                logger.error(f"❌ No se encontró ningún chat para el teléfono {telefono_objetivo}")
                return []

            # ==========================================
            # PASO 2: DETAIL LIST (AQUÍ ESTÁ EL FALLO)
            # ==========================================
            url_detail = 'https://agents.dyna.ai/openapi/v1/conversation/segment/detail_list/'

            payload_detail = {
                "username": AS_ACCOUNT, 
                "segment_code": segment_code, # Aseguramos que esto no sea None
                "create_start_time": "",
                "create_end_time": "",
                "message_source": "",
                "question": "",
                "page": 1,
                "pagesize": 20 
            }

            # DEBUG CRÍTICO: Imprime esto y compáralo con el Body de Postman
            print(f"📨 ENVIANDO PAYLOAD DETALLE: {json.dumps(payload_detail, indent=2)}")

            resp_detail = await client.post(url_detail, headers=headers, json=payload_detail)
            data_detail = resp_detail.json()
            
            if data_detail.get("code") != "000000":
                logger.error(f"❌ Error API Detalle: {data_detail}")
            else:
                total_msgs = data_detail.get("data", {}).get("total", 0)
                print(f"✅ ÉXITO: Mensajes recuperados: {total_msgs}")

            return data_detail

        except Exception as e:
            logger.error(f"Excepción: {e}")
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
    AGENT_KEY = SUMM_AGENTID.strip()
    AGENT_TOKEN = SUMM_TOKEN.strip()
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
        if "last_summary_at" in user and isinstance(user["last_summary_at"], datetime):
            user["last_summary_at"] = user["last_summary_at"].isoformat()

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