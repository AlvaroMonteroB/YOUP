import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from typing import Optional
from datetime import datetime

# 1. Cargar variables de entorno (Seguridad)
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

app = FastAPI(title="Marketing Agent Tool API")

# 2. Configuración de Base de Datos (Motor - Async)
client = AsyncIOMotorClient(MONGO_URI)
db = client.marketing_db  # Nombre de tu base de datos
users_collection = db.users

# 3. Modelos de Datos (Pydantic)
# Esto asegura que el Agente envíe la info correcta
class UserProfile(BaseModel):
    phone_number: str = Field(..., description="Número de teléfono del usuario con código de país")
    preferences: str = Field(..., description="Texto libre con las preferencias de compra o resumen de la conversación")
    source: Optional[str] = Field("bot_marketing", description="Origen del lead")
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 4. Endpoint: Tool para guardar información
@app.post("/save-lead", status_code=status.HTTP_201_CREATED)
async def save_lead(user: UserProfile):
    """
    Guarda o actualiza la información de un usuario.
    Si el teléfono ya existe, actualizamos sus preferencias (Upsert).
    """
    try:
        user_dict = user.model_dump()
        
        # Usamos update_one con upsert=True.
        # Esto es vital: Si el usuario vuelve a hablar, no duplicamos registros,
        # solo actualizamos su historial.
        result = await users_collection.update_one(
            {"phone_number": user.phone_number},
            {"$set": user_dict},
            upsert=True
        )
        
        if result.upserted_id:
            return {"status": "success", "message": "Nuevo usuario registrado", "id": str(result.upserted_id)}
        else:
            return {"status": "success", "message": "Preferencias de usuario actualizadas"}

    except Exception as e:
        # En producción, logguea el error real internamente, pero no lo expongas al cliente
        print(f"Error DB: {e}") 
        raise HTTPException(status_code=500, detail="Error interno al guardar los datos")

@app.get("/get-lead/{phone_number}")
async def get_lead(phone_number: str):
    """
    Busca si ya conocemos a este usuario por su teléfono.
    Útil para que el Agente personalice la charla.
    """
    # Buscamos en la base de datos (excluyendo el _id interno de mongo)
    user = await users_collection.find_one(
        {"phone_number": phone_number},
        {"_id": 0} # No mostramos el ID técnico
    )
    
    if user:
        return {"status": "found", "data": user}
    else:
        # Si no existe, devolvemos un 404 manejado para que el Agente sepa que es nuevo
        raise HTTPException(status_code=404, detail="Usuario nuevo, no hay historial.")

# 5. Health Check (Buena práctica para servidores productivos)
@app.get("/")
async def health_check():
    return {"status": "online", "service": "Marketing Agent Database Tool"}