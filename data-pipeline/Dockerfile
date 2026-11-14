# Container do job NRT (issue #5). O backend inclui como serviço no docker-compose.yml (ver docs/banco.md).
FROM python:3.12-slim

# o pipeline baixa do FIRMS com curl
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py regioes.json ./
COPY migrations ./migrations

# Uma rodada a cada 3 h. A rodada tem trava no banco, então duas nunca rodam ao mesmo tempo,
# e uma falha não derruba o container: a próxima rodada tenta de novo.
CMD ["sh", "-c", "while true; do python job_nrt.py || echo 'job_nrt: rodada falhou'; sleep 10800; done"]
