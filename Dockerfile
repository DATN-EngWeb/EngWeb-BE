FROM python:3.12-slim

# avoid .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (build tools if needed by some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    # for psycopg
    libpq5 \
    libpq-dev \
    pkg-config \
    netcat-openbsd \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8000
RUN dos2unix /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]


