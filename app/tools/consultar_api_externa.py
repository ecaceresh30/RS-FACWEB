"""Integracion con OpenRuc (https://openruc.com) - consulta de datos de una
empresa peruana por RUC.

Contrato real (no es un stub):
    GET https://openruc.com/api/ruc/{ruc}
    200 -> {"ruc", "razon_social", "estado", "condicion", "direccion", "ubigeo",
            "source", "as_of", ...}
    404 -> RUC no encontrado (o fuera de alcance: OpenRuc solo cubre RUC que
           empiezan en 20, personas juridicas)
    400 -> RUC mal formado (no deberia ocurrir: siempre validamos 11 digitos
           antes de llamar)

Sin autenticacion. Usado en dos flujos deterministas (no es una tool del
agente, ver app/main.py):
1. Registro de un RUC nuevo en el login -> se cachea el resultado en `usuarios`.
2. Comando "busca el ruc XXXXXXXXXXX" dentro de la conversacion -> siempre
   consulta en vivo, sin cachear.
"""

import requests

from app.resilience import with_retry

OPENRUC_BASE_URL = "https://openruc.com/api/ruc"
REQUEST_TIMEOUT_SECONDS = 10

CAMPOS_EMPRESA = (
    "ruc",
    "razon_social",
    "estado",
    "condicion",
    "direccion",
    "ubigeo",
    "source",
    "as_of",
)


@with_retry
def consultar_ruc(ruc: str) -> dict | None:
    """Consulta OpenRuc por `ruc`. Devuelve None si no se encuentra (404)."""
    response = requests.get(f"{OPENRUC_BASE_URL}/{ruc}", timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    datos = response.json()
    return {campo: datos.get(campo) for campo in CAMPOS_EMPRESA}
