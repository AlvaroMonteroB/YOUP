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
from sqlalchemy import create_all, create_engine
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
"""
sudo docker-compose up -d ---build

"""



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

# --- CONFIG SQL (Nueva) ---
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 3. Modelos de Datos
class VehicleSpec(Base):
    __tablename__ = "especificaciones_vehiculos"
    id = Column(Integer, primary_key=True, index=True)
    modelo_interno = Column(String(50), unique=True)
    nombre_comercial = Column(String(100))
    autonomia_km = Column(String(150))
    velocidad_maxima = Column(String(100))
    tipo_motor = Column(String(100))
    tipo_bateria = Column(String(100))
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

# TABLA 2: Dispositivos Móviles
class MobileDevice(Base):
    __tablename__ = "dispositivos_moviles"
    id = Column(Integer, primary_key=True, index=True)
    marca = Column(String(50))      # Xiaomi, HONOR
    categoria = Column(String(50))  # Smartphone, Tablet
    modelo = Column(String(100))    # Redmi Note 13
    pantalla = Column(Text)
    procesador = Column(String(150))
    memoria = Column(String(150))
    bateria = Column(String(100))
    carga = Column(String(100))
    camaras = Column(Text)
    sistema_operativo = Column(String(100))
    extras = Column(Text)
    precio_promocion = Column(String(50))
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)


class QueryRequest(BaseModel):
    question: str
    function_call_username: Optional[str] = None

class SqlRequest(BaseModel):
    sql: str

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
    Obtiene el historial del MAIN BOT.
    Args:
        telefono_objetivo (str): Número de teléfono (ej: '525510609610' o '+525510609610')
    """
    try:
        # 1. Carga y Limpieza AGRESIVA de credenciales
        # A veces .env carga comillas extra o saltos de linea que rompen la API
        MAIN_AGENTID = os.getenv("MAIN_AGENTID", "").replace('"', '').replace("'", "").strip()
        MAIN_TOKEN = os.getenv("MAIN_TOKEN", "").replace('"', '').replace("'", "").strip()
        AS_ACCOUNT = os.getenv("AS_ACCOUNT", "").replace('"', '').replace("'", "").strip()

        # Validación rápida para no hacer petición si faltan datos
        if not all([MAIN_AGENTID, MAIN_TOKEN, AS_ACCOUNT]):
            logger.error("Faltan credenciales en variables de entorno")
            return None

        # Headers comunes
        headers = {
            'Content-Type': 'application/json',
            'cybertron-robot-key': MAIN_AGENTID,
            'cybertron-robot-token': MAIN_TOKEN
        }

        # ---------------------------------------------------------
        # PASO 1: OBTENER LISTA DE CHATS
        # ---------------------------------------------------------
        url_list = 'https://agents.dyna.ai/openapi/v1/conversation/segment/get_list/'
        
        payload_list = {
            "username": AS_ACCOUNT, # Ya limpio
            "filter_mode": 0,
            "filter_user_code": "",
            "create_start_time": "",
            "create_end_time": "",
            "message_source": "",
            "page": 1,
            "pagesize": 20 
        }

        # Debug: Ver exactamente qué enviamos (comparar con Postman)
        # logger.info(f"Enviando Payload List: {json.dumps(payload_list)}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp_list = await client.post(url_list, headers=headers, json=payload_list)
            resp_list.raise_for_status() # Lanza error si no es 200 OK
            
            data = resp_list.json()

            if data.get("code") != "000000":
                logger.error(f"API Error Code: {data.get('code')} - {data.get('message')}")
                return None

            lista_chats = data.get("data", {}).get("list", [])
            
            # Debug: Ver cuántos chats devolvió la API
            logger.info(f"Chats encontrados en la cuenta {AS_ACCOUNT}: {len(lista_chats)}")
            
            if not lista_chats:
                logger.warning("La API devolvió una lista vacía. Verifica que AS_ACCOUNT coincida con el Postman.")
                return None

            # ---------------------------------------------------------
            # FILTRADO INTELIGENTE DEL TELÉFONO
            # ---------------------------------------------------------
            # Limpiamos el telefono objetivo de espacios o guiones para buscar mejor
            phone_clean = telefono_objetivo.replace(" ", "").replace("-", "").strip()
            # Si el input no trae '+', probamos buscar con y sin él si es necesario, 
            # pero 'in' suele ser suficiente si user_code es largo.
            
            segment_code = None
            
            for item in lista_chats:
                user_code = item.get("user_code", "")
                # Log para ver contra qué estamos comparando
                # logger.info(f"Comparando {phone_clean} en {user_code}")
                
                if phone_clean in user_code:
                    segment_code = item.get("segment_code")
                    logger.info(f"MATCH ENCONTRADO: {segment_code} para usuario {user_code}")
                    break
            
            if not segment_code:
                logger.warning(f"No se encontró chat para el teléfono: {telefono_objetivo}")
                return None

            # ---------------------------------------------------------
            # PASO 2: OBTENER DETALLE
            # ---------------------------------------------------------
            url_detail = 'https://agents.dyna.ai/openapi/v1/conversation/segment/detail_list/'

            payload_detail = {
                "username": AS_ACCOUNT, 
                "segment_code": segment_code,
                "create_start_time": "",
                "create_end_time": "",
                "message_source": "",
                "question": "",
                "page": 1,
                "pagesize": 20 
            }

            resp_detail = await client.post(url_detail, headers=headers, json=payload_detail)
            resp_detail.raise_for_status()
            
            return resp_detail.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Excepción en get_chat: {e}")
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


def responder(status_code: int, title: str, raw_data: Dict[str, Any]):
    mensaje = raw_data.get("mensaje") or raw_data.get("msgRetorno") or "Operación completada."
    status_str = "error" if status_code >= 400 else "exito"
    
    return JSONResponse(status_code=status_code, content={
        "raw": {"status": status_str, **raw_data},
        "markdown": f"**{title}**\n\n{mensaje}",
        "type": "markdown",
        "desc": f"{mensaje}\n\n"
    })

async def enviar_whatsapp_logic(phone: str, image_url: str):
    """Simulación de envío de WhatsApp"""
    logger.info(f"--- ENVIANDO WHATSAPP a {phone}: {image_url} ---")
    # Aquí tu código real de Twilio/Meta
    pass

async def call_agent_api(prompt: str) -> str:
    """Función auxiliar para llamar al agente y obtener texto limpio"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            AGENT_API_URL,
            headers={
                'Content-Type': 'application/json',
                'cybertron-robot-key': QUERY_KEY,   # Usando las keys solicitadas
                'cybertron-robot-token': QUERY_TOKEN
            },
            json={"username": AS_ACCOUNT, "question": prompt},
            timeout=45.0 # Un poco más de tiempo para análisis
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("answer", "")

# --- 4. ENDPOINT PRINCIPAL ---

@app.post("/query-generator")
async def query_generator(request: QueryRequest, db: Session = Depends(get_db)):
    question = request.question
    
    # --- VALIDACIÓN INICIAL ---
    if not question or not isinstance(question, str) or not question.strip():
        return JSONResponse(status_code=400, content={
            "raw": {"error": "Bad Request", "details": 'El campo "question" es requerido.'},
            "markdown": "No hay datos.", "type": "markdown", "desc": "⚠️ Error: Pregunta vacía."
        })

    try:
        logger.info(f"1. Iniciando proceso para: {question}")

        # ==============================================================================
        # PASO 1: NLP -> SQL (Llamada al Agente)
        # ==============================================================================
        schema_prompt = f"""
        Actúa como un ingeniero de datos experto. Convierte la siguiente pregunta en lenguaje natural a una consulta SQL PostgreSQL válida.
        
        ESQUEMA DE TABLAS:
        - marcas (id_marca, nombre_marca)
        - modelos (id_modelo, id_marca, nombre_modelo)
        - pictures (id, url) -> IMPORTANTE: El resultado debe incluir 'image_url' si existe.
        - especificaciones (id_especificacion, id_modelo, bateria_v_ah, potencia_w, velocidad_maxima_km_h, rango_km, peso_neto_kg...)
        - precios (id_precio, id_modelo, minorista_mxn)

        Pregunta: "{question}"

        REGLAS:
        1. Devuelve SOLO el código SQL (SELECT).
        2. No uses Markdown (```sql).
        3. Si no puedes, devuelve "ERROR".
        """
        
        sql_generated = await call_agent_api(schema_prompt)
        
        # Limpieza de la respuesta del agente
        sql_clean = sql_generated.replace("```sql", "").replace("```", "").replace(";", "").strip()
        
        if not sql_clean.upper().startswith("SELECT"):
            raise Exception(f"El agente no generó un SQL válido: {sql_clean}")

        logger.info(f"2. SQL Generado: {sql_clean}")

        # ==============================================================================
        # PASO 2: EJECUTAR SQL EN BASE DE DATOS
        # ==============================================================================
        result_proxy = db.execute(text(sql_clean))
        keys = result_proxy.keys()
        db_results = [dict(zip(keys, row)) for row in result_proxy]
        
        logger.info(f"3. Resultados DB encontrados: {len(db_results)}")

        # ==============================================================================
        # PASO 3: LÓGICA WHATSAPP (Side Effect)
        # ==============================================================================
        if db_results and "image_url" in db_results[0] and db_results[0]["image_url"]:
            username = request.function_call_username
            if username and isinstance(username, str):
                raw_phone = username.split("--")[-1] if "--" in username else username
                try:
                    await enviar_whatsapp_logic(raw_phone, db_results[0]["image_url"])
                    # Opcional: Eliminar la URL para que no sature el contexto del agente en el paso 4
                    # Pero a veces es bueno dejarla para que el agente sepa que hay foto.
                    # Si quieres borrarla descomenta abajo:
                    # for row in db_results:
                    #    if "image_url" in row: del row["image_url"]
                except Exception as e:
                    logger.error(f"Error enviando WhatsApp: {e}")

        # ==============================================================================
        # PASO 4: DATOS -> LENGUAJE NATURAL (Segunda llamada al Agente)
        # ==============================================================================
        
        if not db_results:
            final_message = "No encontré información en la base de datos que coincida con tu búsqueda."
        else:
            # Convertimos los datos a string JSON para pasárselos al agente
            data_string = json.dumps(db_results, default=str, ensure_ascii=False)
            
            analysis_prompt = f"""
            Actúa como un asistente de ventas experto en movilidad eléctrica.
            
            CONTEXTO:
            El usuario preguntó: "{question}"
            
            DATOS ENCONTRADOS EN LA BASE DE DATOS:
            {data_string}
            
            INSTRUCCIÓN:
            Responde amablemente a la pregunta del usuario basándote ESTRICTAMENTE en los datos encontrados arriba.
            - Si hay precios, formatéalos con signo de pesos.
            - Destaca las características principales.
            - Sé conciso y persuasivo.
            """
            
            logger.info("4. Enviando datos al agente para interpretación...")
            final_message = await call_agent_api(analysis_prompt)

        # ==============================================================================
        # PASO 5: RETORNO FINAL
        # ==============================================================================
        return responder(
            status_code=200,
            title="Asistente Virtual",
            raw_data={
                "mensaje": final_message, # El mensaje generado por la IA
                "data_raw": db_results,   # Los datos crudos (opcional, útil para frontend)
                "sql_debug": sql_clean    # Debug (opcional)
            }
        )

    except Exception as e:
        logger.error(f"Error crítico en query_generator: {e}")
        return responder(500, "Error en el sistema", {"mensaje": f"Ocurrió un problema procesando tu solicitud: {str(e)}"})


            

@app.get("/")
async def health_check():
    return {"status": "online", "service": "Marketing Agent Database Tool"}
