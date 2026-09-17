"""Punto de entrada CLI del agente conversacional.

Identifica al usuario por RUC, recupera o crea su conversacion en Supabase,
y mantiene el historial persistido en cada turno.
"""

import os
import sys

from app.conversation import (
    RUC_PATTERN,
    RucInvalidoError,
    RucNoEncontradoError,
    TurnoError,
    iniciar_sesion,
    procesar_turno,
)

EXIT_COMMANDS = {"salir", "exit", "quit"}

# La consola de Windows suele usar cp1252, que no puede codificar todos los
# caracteres Unicode que puede devolver el modelo (ej. espacios especiales,
# comillas tipograficas). Forzar UTF-8 evita que print() rompa la aplicacion.
sys.stdout.reconfigure(encoding="utf-8")


def _tracing_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "").lower() == "true" or os.getenv(
        "LANGCHAIN_TRACING_V2", ""
    ).lower() == "true"


def _read_ruc() -> str:
    while True:
        ruc = input("RUC: ").strip()
        if RUC_PATTERN.fullmatch(ruc):
            return ruc
        print("El RUC debe tener exactamente 11 digitos numericos.")


def main() -> None:
    print(f"Tracing (LangSmith): {'activo' if _tracing_enabled() else 'inactivo'}")

    ruc = _read_ruc()

    try:
        sesion = iniciar_sesion(ruc)
    except RucInvalidoError as exc:
        print(str(exc))
        return
    except RucNoEncontradoError as exc:
        print(f"{exc} No se puede registrar.")
        return
    except Exception as exc:
        print(f"No se pudo conectar con Supabase/OpenRuc ({type(exc).__name__}: {exc}).")
        return

    usuario = sesion.usuario
    if sesion.es_nuevo:
        print(f"RUC {usuario['ruc']} ({usuario['razon_social']}) registrado. Nueva conversacion iniciada.")
    else:
        print(
            f"Bienvenido de nuevo, {usuario['razon_social']} (RUC {usuario['ruc']}). "
            "Continuando conversacion existente."
        )

    print("Escribe tu mensaje (o 'salir' para terminar).")
    while True:
        user_input = input("> ").strip()
        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break

        try:
            resultado = procesar_turno(sesion, user_input)
        except TurnoError as exc:
            print(f"{exc} Intenta de nuevo.")
            continue

        for aviso in resultado.avisos:
            print(f"(Aviso: {aviso})")
        print(resultado.respuesta)


if __name__ == "__main__":
    main()
