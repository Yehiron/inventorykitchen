FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear el directorio data donde vivirá la DB
RUN mkdir -p /app/data

EXPOSE 8080

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8080", "app:app"]
