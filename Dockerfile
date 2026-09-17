FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app
COPY web web
COPY supabase supabase

EXPOSE 8000

# Variables de entorno (.env) se pasan en runtime via --env-file, no se
# hornean en la imagen.
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
