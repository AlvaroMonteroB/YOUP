import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 1. Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
LOG_FILE_PATH = "logs/app.log"

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
    preferences: str = Field(..., description="Texto libre con preferencias o resumen")
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
        "desc": f"**{title}**\n\n{mensaje}"
    })

# 5. Endpoints

@app.post("/save-lead", response_model=AgentResponse)
async def save_lead(user: UserProfile):
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
                "mensaje": f"¡Hola! ¿En qué podemos ayudarle hoy?⁄n Estamos aquí para darte cualquier información a cerca de los productos que ofrecemos"
            }
            return responder(201, "Registro Exitoso", raw_data)
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


@app.get("/get-lead/{phone_number}", response_model=AgentResponse)
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

@app.get("/")
async def health_check():
    return {"status": "online", "service": "Marketing Agent Database Tool"}