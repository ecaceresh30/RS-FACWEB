"""API web del agente conversacional (MVP).

Sesion en memoria por RUC (un solo proceso, sin multi-worker) - suficiente
para probar el modelo en el VPS. Sirve tambien el frontend estatico (web/).
"""

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.conversation import (
    RucInvalidoError,
    RucNoEncontradoError,
    Sesion,
    TurnoError,
    iniciar_sesion,
    procesar_turno_stream,
    reiniciar_historial,
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


class ResetRequest(BaseModel):
    ruc: str


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
    """Responde en streaming NDJSON (una linea JSON por evento): primero un
    evento {"tipo": "fase", "texto": ...} apenas se sabe que fuente se va a
    consultar (conocimiento.pdf, conocimiento_sire.pdf, internet, OpenRuc, o una
    combinacion), y al final {"tipo": "resultado", ...} con la respuesta. El
    frontend (web/app.js) lo usa para mostrar un indicador de progreso real
    mientras se espera la respuesta del LLM."""
    sesion = _SESIONES.get(body.ruc)
    if sesion is None:
        raise HTTPException(status_code=400, detail="Primero inicia sesion con /api/login.")

    mensaje = body.mensaje.strip()
    if not mensaje:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio.")

    def event_stream():
        try:
            for tipo, payload in procesar_turno_stream(sesion, mensaje):
                if tipo == "fase":
                    evento = {"tipo": "fase", "texto": payload}
                else:
                    evento = {
                        "tipo": "resultado",
                        "respuesta": payload.respuesta,
                        "avisos": payload.avisos,
                        "sugerencias": payload.sugerencias,
                        "tabla_cartera": payload.tabla_cartera,
                    }
                yield json.dumps(evento, ensure_ascii=False) + "\n"
        except TurnoError as exc:
            yield json.dumps({"tipo": "error", "detalle": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/api/reset")
def reset(body: ResetRequest):
    """Borra el historial de conversaciones del RUC logueado (Supabase) y arranca
    una conversacion nueva vacia. Usado por el boton "Eliminar historial" del
    frontend (web/app.js)."""
    sesion = _SESIONES.get(body.ruc)
    if sesion is None:
        raise HTTPException(status_code=400, detail="Primero inicia sesion con /api/login.")

    try:
        reiniciar_historial(sesion)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo eliminar el historial ({type(exc).__name__}).",
        ) from exc

    return {"historial": sesion.messages}


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="web", html=True), name="web")
