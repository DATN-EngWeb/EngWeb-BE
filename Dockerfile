FROM python:3.12-slim

# avoid .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# system deps (build tools if needed by some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    # for psycopg
    libpq5 \
    libpq-dev \
    pkg-config \
    netcat-openbsd \
    dos2unix \
    # for psql command (seed SQL files)
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Ho_Chi_Minh
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# install pipenv
RUN pip install --no-cache-dir pipenv

# copy Pipfile & Pipfile.lock first (for caching layers)
COPY Pipfile Pipfile.lock ./

# install dependencies (into system, not virtualenv)
RUN pipenv install --deploy --system

# copy project
COPY . .

EXPOSE 8000

RUN dos2unix /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]