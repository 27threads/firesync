# infra

Tudo o que põe o sistema no ar na VPS ([docs/arquitetura.md](../docs/arquitetura.md), ponto 12).

- **Frente responsável:** C, com a frente A no serviço do banco e no job NRT.
- **O que vai aqui:**
  - `docker-compose.yml`: serviços `db` (Postgres + PostGIS), `api`, `web` e `nrt` (job a cada 3 h). O trecho do `db` está em [docs/banco.md](../docs/banco.md);
  - configuração do servidor web (HTTPS e o caminho `/api`);
  - `.env.example`, com os nomes das variáveis e sem valores reais;
  - instruções de deploy e de backup do banco.
- **O que não vai aqui:** os `Dockerfile` de cada serviço ficam na pasta do próprio serviço (`backend/`, `frontend/`, `data-pipeline/`).

Regras que valem aqui:

- Segredos (`POSTGRES_PASSWORD`, `FIRMS_MAP_KEY`) só no `.env` da VPS, nunca no git.
- As migrations ficam em `data-pipeline/migrations/` e são montadas no serviço `db`.
