# infra

Tudo o que põe o sistema no ar na VPS ([docs/arquitetura.md](../docs/arquitetura.md), ponto 12).

- **Frente responsável:** C, com a frente A no serviço do banco e no job NRT.
- **O que vai aqui:**
  - `docker-compose.yml`: serviços `db` (Postgres + PostGIS), `api`, `job-nrt` (job a cada 3 h), `job-risco` (risco dos 14 dias por célula, 1 vez por dia) e `tunnel` (Cloudflare Tunnel até a API). O front não roda na VPS: fica no Cloudflare;
  - `.env.example`, com os nomes das variáveis e sem valores reais.
- **Passo a passo e segurança:** [docs/deploy.md](../docs/deploy.md).
- **O que não vai aqui:** os `Dockerfile` de cada serviço ficam na pasta do próprio serviço (`backend/`, `data-pipeline/`).

Regras que valem aqui:

- Segredos (`POSTGRES_PASSWORD`, `API_DB_PASSWORD`, `FIRMS_MAP_KEY`, `CLOUDFLARE_TUNNEL_TOKEN`) só no `.env` da VPS, nunca no git.
- As migrations ficam em `data-pipeline/migrations/` e são montadas no serviço `db`.
- **O rate limit tem que ver o IP real do usuário:** atrás do túnel, todo pedido chega vindo do `cloudflared`. O compose define `CLIENT_IP_HEADER=CF-Connecting-IP` no serviço `api` ([deploy.md](../docs/deploy.md)). Sem isso, todos os usuários dividem o mesmo limite.
