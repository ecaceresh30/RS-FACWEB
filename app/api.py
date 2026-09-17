"""API web del agente conversacional (MVP).

Sesion en memoria por RUC (un solo proceso, sin multi-worker) - suficiente
para probar el modelo en el VPS. Sirve tambien el frontend estatico (web/).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.conversation import (
    RucInvalidoError,
    RucNoEncontradoError,
    Sesion,
    TurnoError,
    iniciar_sesion,
    procesar_turno,
)

app = FastAPI(title="Agente Conversacional - MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MVP: estado de sesion en memoria del proceso, indexado por RUC.
_SESIONES: dict[str, Sesion] = {}


class LoginRequest(BaseModel):
    ruc: str


class ChatRequest(BaseModel):
    ruc: str
    mensaje: str


@app.post("/api/login")
def login(body: LoginRequest):
    try:
        sesion = iniciar_sesion(body.ruc)
    except RucInvalidoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RucNoEncontradoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar con Supabase/OpenRuc ({type(exc).__name__}).",
        ) from exc

    _SESIONES[body.ruc] = sesion

    return {
        "ruc": sesion.usuario["ruc"],
        "razon_social": sesion.usuario["razon_social"],
        "es_nuevo": sesion.es_nuevo,
        "historial": sesion.messages,
    }


@app.post("/api/chat")
def chat(body: ChatRequest):
    sesion = _SESIONES.get(body.ruc)
    if sesion is None:
        raise HTTPException(status_code=400, detail="Primero inicia sesion con /api/login.")

    mensaje = body.mensaje.strip()
    if not mensaje:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio.")

    try:
        resultado = procesar_turno(sesion, mensaje)
    except TurnoError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"respuesta": resultado.respuesta, "avisos": resultado.avisos}


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="web", html=True), name="web")
