FROM python:3.11-slim

# System deps for slither / mythril / solc-select
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential libssl-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install a recent Solidity compiler
RUN solc-select install 0.8.24 && solc-select use 0.8.24

# Persist audit history outside the image
VOLUME ["/app/data"]
ENV AUDIT_DB_PATH=/app/data/audit_history.db

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
