# Container do job NRT (issue #5). O backend inclui como serviço no docker-compose.yml (ver docs/banco.md).
FROM python:3.12-slim

# o pipeline baixa do FIRMS com curl
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py regioes.json lugares.json ./
COPY migrations ./migrations
# o job de risco (risco_celulas.py) importa as funções do experimento desta pasta
COPY validacao/*.py ./validacao/

# Uma rodada a cada 3 h. A rodada tem trava no banco, então duas nunca rodam ao mesmo tempo,
# e uma falha não derruba o container: a próxima rodada tenta de novo. A falha já sai no log como
# `nrt_run_failed` (JSON, com a etapa e o erro), então o laço não escreve nada fora do formato.
CMD ["sh", "-c", "while true; do python job_nrt.py || true; sleep 10800; done"]
