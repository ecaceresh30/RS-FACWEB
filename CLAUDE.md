# CLAUDE.md — Contexto del proyecto

Este archivo complementa a `playbook.md`.

`playbook.md` define el comportamiento general del AI Software Architect.
`CLAUDE.md` contiene únicamente el **contexto, decisiones y reglas específicas de este proyecto**.

## Relación con playbook.md

Antes de trabajar en cualquier tarea:

1. Aplicar las reglas de `playbook.md`.
2. Aplicar el contexto y restricciones de este archivo.
3. Las decisiones específicas de este proyecto deben respetarse.
4. Si una decisión específica requiere modificar otros componentes, seguir el proceso de confirmación definido en `playbook.md`.

---

## Contexto del proyecto

Agente conversacional empresarial construido con:

- Python
- LangChain
- OpenAI (`gpt-4.1`)
- Supabase / PostgreSQL
- pgvector
- `.env`

### Identificación de usuarios

El usuario se identifica mediante **RUC** (11 dígitos numéricos).

- Si el RUC no existe: registrar el usuario en Supabase e iniciar una conversación nueva.
- Si el RUC ya existe: recuperar sus datos, buscar conversaciones existentes, recuperar el historial correspondiente y continuar la conversación.

El historial conversacional debe persistirse en Supabase.

---

## Base de conocimiento

Archivo fuente: `conocimiento.pdf`.

Este documento constituye la base de conocimiento inicial del agente.

Pipeline RAG:

```
PDF → chunks → embeddings → Supabase/pgvector → retrieval → LLM
```

Tool asociada: `buscar_conocimiento`.

---

## Tools

El agente tendrá inicialmente tres tools.

### `buscar_conocimiento`

Consulta la base de conocimiento mediante RAG utilizando Supabase/pgvector.

### `busqueda_internet`

Búsqueda en Internet. Proveedor: **Tavily** (https://tavily.com). Solo se activa
cuando el usuario escribe explícitamente "busca en internet" en su mensaje
(gating determinista, no depende del criterio del LLM).

### `consultar_api_externa`

Consulta datos de una empresa por RUC vía **OpenRuc** (https://openruc.com):

```
GET https://openruc.com/api/ruc/{ruc}
```

Sin autenticación. Respuesta: `ruc`, `razon_social`, `estado`, `condicion`,
`direccion`, `ubigeo`, `source`, `as_of`. 404 si el RUC no existe (o está
fuera de alcance: OpenRuc solo cubre RUC de personas jurídicas, que empiezan
en 20).

Dos usos deterministas (no es una tool del agente, ver `app/main.py`):

1. Al registrar un RUC nuevo en el login: se consulta y se cachea el
   resultado en `usuarios` (logins posteriores usan el dato cacheado, no
   vuelven a llamar a la API).
2. Comando `"busca el ruc XXXXXXXXXXX"` dentro de la conversación: consulta
   en vivo cualquier RUC, sin cachear. Responde con los datos encontrados o
   un mensaje de "no encontrado". Cita siempre `Fuente: OpenRuc`.

---

## Configuración

- Configuración y secretos mediante `.env`.
- Modelo inicial: `gpt-4.1`.
- Las credenciales nunca deben estar hardcodeadas.
- Utilizar `.env.example` cuando corresponda.

---

## Reglas específicas del proyecto

- Mantener `gpt-4.1` salvo autorización explícita.
- Mantener Supabase como persistencia principal.
- Utilizar pgvector para el RAG inicial.
- No reemplazar Supabase por Qdrant sin autorización.
- No inventar reglas de negocio.
- Mantener separadas las responsabilidades de usuarios, conversaciones, conocimiento y tools.
- Las tools deben estar desacopladas del núcleo conversacional.
- Mantener la arquitectura preparada para incorporar nuevas tools.
- No introducir LangGraph, multi-agent, microservicios u otra infraestructura adicional salvo que exista una necesidad concreta.
- No modificar decisiones arquitectónicas existentes sin evaluar su impacto.
- Si una decisión afecta otros componentes, seguir el proceso de confirmación definido en `playbook.md`.
- Priorizar una solución simple, modular y extensible.

---

## Objetivo funcional inicial

El sistema debe permitir:

1. Registrar al usuario mediante RUC.
2. Recuperar usuarios existentes.
3. Recuperar historial conversacional.
4. Continuar conversaciones existentes.
5. Iniciar conversaciones nuevas.
6. Utilizar `gpt-4.1`.
7. Consultar `conocimiento.pdf` mediante RAG.
8. Realizar búsquedas mediante `busqueda_internet`.
9. Consultar datos de empresas por RUC mediante `consultar_api_externa` (OpenRuc).
10. Persistir las conversaciones en Supabase.