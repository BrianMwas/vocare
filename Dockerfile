# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port for FreeSWITCH socket connection
EXPOSE 8000

CMD ["python", "main.py", "dev"]
