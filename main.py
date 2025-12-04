import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 1. Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
LOG_FILE_PATH = "logs/app.log"

# --- CONFIGURACIÓN DE LOGS ---
# Crear carpeta de logs si no existe
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configurar el logger
logger = logging.getLogger("marketing_agent")
logger.setLevel(logging.INFO)

# Handler que rota los logs:
# when="midnight": rota cada noche
# interval=1: cada 1 día
# backupCount=7: mantiene los últimos 7 días, borra los anteriores
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
    """Modelo estandarizado para respuestas al Agente"""
    raw: Any = Field(..., description="Datos crudos en JSON/Dict")
    markdown: str = Field(..., description="Respuesta legible para mostrar al usuario o razonar")
    type: str = Field(..., description="Tipo de dato (text, json, file, etc.)")
    desc: str = Field(..., description="Descripción técnica de lo ocurrido")

class Preferences(BaseModel):
    preferences: str = Field(..., description="Texto libre con preferencias o resumen")

# 4. Helper para respuestas estandarizadas
def create_response(raw_data: Any, markdown: str, desc: str, type_str: str = "json") -> AgentResponse:
    return AgentResponse(
        raw=raw_data,
        markdown=markdown,
        type=type_str,
        desc=desc
    )

# 5. Endpoints

@app.post("/save-lead", status_code=status.HTTP_200_OK, response_model=AgentResponse)
async def save_lead(user: UserProfile):
    """
    Guarda información extrayendo el teléfono limpio.
    Respuesta en formato OpenAPI estricto.
    """
    try:
        # Lógica solicitada para extraer el teléfono
        # Validamos si existe '--' en el string de entrada
        full_username = user.function_call_username
        raw_phone = full_username.split("--")[-1] if "--" in full_username else full_username
        
        # Preparamos el documento para Mongo
        user_dict = user.model_dump()
        user_dict["phone_number"] = raw_phone  # Guardamos el teléfono limpio explícitamente

        # Log de la acción
        logger.info(f"Intentando guardar/actualizar lead: {raw_phone} (Origen: {full_username})")

        # Upsert en la base de datos
        result = await users_collection.update_one(
            {"phone_number": raw_phone},
            {"$set": user_dict},
            upsert=True
        )

        log_msg = f"Lead procesado correctamente: {raw_phone}"
        logger.info(log_msg)

        # Construir respuesta estandarizada
        if result.upserted_id:
            msg_md = f"✅ Nuevo usuario registrado con éxito. Teléfono: {raw_phone}."
            raw_resp = {"id": str(result.upserted_id), "action": "created", "phone": raw_phone}
        else:
            msg_md = f"🔄 Preferencias actualizadas para el usuario {raw_phone}."
            raw_resp = {"id": raw_phone, "action": "updated", "phone": raw_phone}

        return create_response(
            raw_data=raw_resp,
            markdown=msg_md,
            type="json",
            desc="Operación de base de datos exitosa"
        )

    except Exception as e:
        error_msg = f"Error DB save_lead: {str(e)}"
        logger.error(error_msg)
        # Incluso en error, intentamos devolver formato JSON si es posible, 
        # o dejamos que FastAPI lance el 500, pero loggeando primero.
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/get-lead/{phone_number}", response_model=AgentResponse)
async def get_lead(phone_number: str):
    """
    Busca usuario y retorna formato estandarizado.
    """
    logger.info(f"Buscando lead: {phone_number}")
    
    user = await users_collection.find_one(
        {"phone_number": phone_number},
        {"_id": 0}
    )
    
    if user:
        # Convertir objetos datetime a str para evitar errores de serialización JSON
        if "created_at" in user and isinstance(user["created_at"], datetime):
            user["created_at"] = user["created_at"].isoformat()

        logger.info(f"Lead encontrado: {phone_number}")
        
        return create_response(
            raw_data=user,
            markdown=f"📋 Información encontrada para **{phone_number}**:\n\nIntereses: {user.get('preferences', 'Sin datos')}",
            type="json",
            desc="Usuario encontrado en base de datos"
        )
    else:
        logger.warning(f"Lead no encontrado: {phone_number}")
        # En vez de romper el flujo con error 404, devolvemos una respuesta
        # estructurada indicando que no existe (útil para lógica de agentes).
        return create_response(
            raw_data={"found": False, "phone": phone_number},
            markdown=f"No encontré registros previos para el número {phone_number}.",
            type="json",
            desc="Usuario no encontrado"
        )

@app.post("/get-logs")
async def get_system_logs():
    """
    Endpoint POST para descargar/ver los logs del sistema.
    """
    try:
        if os.path.exists(LOG_FILE_PATH):
            logger.info("Acceso a descarga de logs solicitado.")
            # Retorna el archivo directamente
            return FileResponse(
                path=LOG_FILE_PATH, 
                filename="system_logs.txt", 
                media_type="text/plain"
            )
        else:
            return create_response(
                raw_data={"error": "no_logs"},
                markdown="No hay archivo de logs disponible actualmente.",
                type="error",
                desc="Archivo de log inexistente"
            )
    except Exception as e:
        logger.error(f"Error al leer logs: {e}")
        raise HTTPException(status_code=500, detail="Error leyendo logs")

@app.get("/")
async def health_check():
    return {"status": "online", "service": "Marketing Agent Database Tool"}