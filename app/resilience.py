"""Reintentos para llamadas de red transitorias (Supabase, Tavily).

No reintenta errores de negocio/autenticacion (4xx, ValueError, etc.) -
solo fallas de transporte (timeouts, conexion caida), que son las unicas
donde reintentar tiene sentido.
"""

import httpx
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

RETRYABLE_EXCEPTIONS = (
    httpx.TransportError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)

with_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
)
