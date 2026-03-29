# ---- Base image ----
FROM python:3.11-slim

# ---- Environment settings ----
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---- System dependencies (needed for Telethon + networking) ----
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Set working directory ----
WORKDIR /app

# ---- Install Python dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy application code ----
COPY . .

# ---- Expose port (Railway injects $PORT, this is just documentation) ----
EXPOSE 8000

# ---- Start FastAPI ----
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]