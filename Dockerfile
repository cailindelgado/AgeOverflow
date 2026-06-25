FROM python:3.13-slim 

RUN apt-get update && apt-get install -y pipx  && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pipx ensurepath
RUN pipx install poetry

WORKDIR /app

COPY pyproject.toml ./
RUN pipx run poetry install --no-root

COPY GCAS GCAS

CMD ["bash", "-c", "sleep 10 && pipx run poetry run flask --app GCAS run --host 0.0.0.0 --port 8080"]