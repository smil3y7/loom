# Loom
# Dockerfile

FROM python:3.12-slim

WORKDIR /loom

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copy engine code
COPY lib/ ./lib/
COPY adapters/ ./adapters/
COPY cli/ ./cli/
COPY api/ ./api/
COPY loom.py .

# Mount points
RUN mkdir -p /loom/sources/dreamdb \
             /loom/sources/lab \
             /loom/sources/oneiro \
             /loom/storage

# Expose API port
EXPOSE 8000

# Zaženi API strežnik + ohrani CLI dostop prek docker exec
CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
