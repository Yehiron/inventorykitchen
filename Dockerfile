# ─────────────────────────────────────────────────────────────
# DOCKERFILE — Kitchen Inventory
#
# ¿Qué es esto?
# Un archivo de texto con instrucciones para construir una
# "caja" (contenedor) que contiene exactamente lo que nuestra
# app necesita para funcionar, en cualquier computadora o servidor.
# ─────────────────────────────────────────────────────────────

# ── 1. IMAGEN BASE ───────────────────────────────────────────
# "Partir de" una imagen oficial de Python 3.11 en su versión
# más ligera (slim = sin herramientas extra que no necesitamos).
# Es como decir: "dame una computadora nueva con Python ya instalado".
FROM python:3.11-slim

# ── 2. DIRECTORIO DE TRABAJO ─────────────────────────────────
# Dentro del contenedor, todos los archivos vivirán en /app.
# Es equivalente a hacer "mkdir /app && cd /app".
WORKDIR /app

# ── 3. INSTALAR DEPENDENCIAS ─────────────────────────────────
# Primero copiamos SOLO el requirements.txt (no el resto del código).
# Esto es un truco de rendimiento: Docker cachea capas. Si el código
# cambia pero requirements.txt no, Docker no reinstala las librerías.
COPY requirements.txt .

# Instala las librerías de Python listadas en requirements.txt.
# --no-cache-dir = no guarda el caché de pip (ahorra espacio en la imagen).
RUN pip install --no-cache-dir -r requirements.txt

# ── 4. COPIAR EL CÓDIGO ──────────────────────────────────────
# Ahora sí copiamos todo el código al contenedor.
# El primer "." = todo lo que está en nuestra carpeta local.
# El segundo "." = el WORKDIR (/app) dentro del contenedor.
COPY . .

# ── 5. PUERTO ────────────────────────────────────────────────
# Le decimos a Docker que nuestra app escucha en el puerto 8080.
# Esto es solo documentación (no abre el puerto por sí solo).
EXPOSE 8080

# ── 6. COMANDO DE ARRANQUE ───────────────────────────────────
# Cuando Render inicie el contenedor, ejecuta este comando.
#
# gunicorn = servidor web de producción (más robusto que Flask dev)
# --workers 2 = 2 procesos paralelos para manejar peticiones
# --bind 0.0.0.0:8080 = escucha en todas las interfaces en el puerto 8080
# "app:app" = en el archivo "app.py", usa la variable "app" (la instancia Flask)
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8080", "app:app"]
