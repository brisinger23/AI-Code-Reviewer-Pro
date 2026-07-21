# Portable container image — works on any free host that runs Docker
# (Koyeb, Fly.io, Google Cloud Run, Railway, etc.) as well as locally.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    GRADIO_SERVER_NAME=0.0.0.0

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

EXPOSE 7860

CMD ["python", "app.py"]
