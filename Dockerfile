# Reliability Cockpit Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose FastAPI dashboard port
EXPOSE 8000

# Run FastAPI dashboard
CMD ["uvicorn", "dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
