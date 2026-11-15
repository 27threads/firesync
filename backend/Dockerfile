# Container da API. Build a partir da raiz do repositório (precisa de config/):
# docker build -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app
COPY backend/pyproject.toml backend/
COPY backend/src backend/src
RUN pip install --no-cache-dir ./backend
COPY config ./config
# Instalado como pacote, o caminho padrão das regras não aponta mais para a raiz do repo.
ENV ALERT_RULES_PATH=/app/config/alert_rules.json

RUN useradd --create-home --uid 10001 api
USER api
EXPOSE 8000
CMD ["uvicorn", "backend.adapters.inbound.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
