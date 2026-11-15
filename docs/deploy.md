# Deploy

Nov 15, 2026 · frente C · decisão 12 de [arquitetura.md](arquitetura.md)

O front fica no Cloudflare. Banco, API, job NRT e job de risco ficam na VPS, com `docker compose`. No ar desde 15/11/2026: front em <https://firesync.nogranlabs.com.br> e API em <https://firesync-api.nogranlabs.com.br>. A VPS não abre nenhuma porta para a internet: o único caminho de fora para dentro é o Cloudflare Tunnel até a API.

```
navegador ──> Cloudflare (front estático, firesync.nogranlabs.com.br)
navegador ──> Cloudflare (firesync-api.nogranlabs.com.br) ──túnel──> VPS: api ──> db
                                                    VPS: job-nrt ──> FIRMS
                                                    VPS: job-risco ──> db (risco_celulas)
```

**Por que assim:** o front é só arquivo estático e fica mais rápido na CDN do Cloudflare para o jurado em qualquer país. Com o túnel, o IP da VPS não aparece, o HTTPS vem pronto e não existe porta aberta para atacar.

## Front no Cloudflare (Workers, só arquivos estáticos)

O repositório é um monorepo. O Cloudflare clona o repo inteiro e faz o build a partir de `frontend/`. O `frontend/wrangler.jsonc` diz para o `wrangler deploy` publicar o `dist/` e responder `index.html` em qualquer rota. Sem esse arquivo, o wrangler tenta se configurar sozinho e falha com Vite 5.

Em **Workers & Pages → firesync-prd → Settings → Build**:

| Campo | Valor |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm run build` (o Cloudflare já roda `npm ci` antes) |
| Deploy command | `npx wrangler deploy` |
| Build watch paths | `frontend/*` e `docs/api-exemplo.json` (o `App.tsx` importa esse JSON) |
| Build variable | `VITE_API_URL=https://firesync-api.nogranlabs.com.br` |

- O `VITE_API_URL` é uma variável de **build**, não de runtime: ela entra no JavaScript na hora do `vite build`. Mudou o valor, faça um novo deploy.
- Toda variável `VITE_` fica pública no JavaScript. Segredo nunca vai em `VITE_`.
- Os headers de segurança (CSP, HSTS, `nosniff`) ficam em `frontend/public/_headers`. Uma origem nova no front (outro servidor de tiles, por exemplo) precisa entrar no CSP desse arquivo.

## Banco, API e jobs na VPS

Tudo em [`infra/docker-compose.yml`](../infra/docker-compose.yml). Nenhum serviço tem `ports:`.

1. Copie `infra/.env.example` para `infra/.env` (ao lado do compose, que só lê o `.env` da própria pasta) e preencha. O `.env` nunca vai para o git.
2. No Cloudflare, em **Zero Trust → Networks → Tunnels**, crie um túnel, copie o token para `CLOUDFLARE_TUNNEL_TOKEN` e adicione o public hostname `firesync-api.nogranlabs.com.br` → `http://api:8000`. O hostname leva `firesync` porque o domínio atende outros projetos: um nome genérico como `api.` disputa o registro DNS com eles. Já o serviço fica `http://api:8000`, porque `api` é o nome do serviço na rede do compose e só os containers do firesync estão nela.
3. `FRONTEND_ORIGIN` é a origem exata do front, sem barra no fim. É a única que o CORS aceita.
4. **Na primeira vez**, siga o roteiro de carga do [banco.md](banco.md#carga-na-vps-roteiro), que sobe só o `db`, restaura o dump e cria o usuário `firesync_api`. Com a API e o job no ar, o `pg_restore --clean` disputaria o banco com as conexões, o job rodaria no banco vazio e a API, que confere os metadados ao subir, ficaria reiniciando.
5. Depois da carga, na VPS, a partir de `infra/`: `docker compose up -d --build`.

**API só com leitura:** a API usa o usuário `firesync_api` (só `SELECT`, `statement_timeout` de 30 s), criado no roteiro de carga. Um erro na API não apaga dados, e uma consulta pesada não segura o pool. O pipeline, o job NRT e o job de risco usam o `firesync`, que escreve.

**Job de risco:** o serviço `job-risco` usa a mesma imagem do `job-nrt` e roda `risco_celulas.py --gravar` uma vez por dia: treina o modelo, pontua as células e grava em `risco_celulas`. As faixas vêm do `config/risk_rules.json`, montado só para leitura. A API esconde notas mais velhas que `RISK_MAX_AGE_DAYS` dias (padrão 2, tabela de variáveis no [backend/README.md](../backend/README.md)). Na VPS o `.env` usa 10: o job grava uma nota por dia, e o valor maior só pesa se ele parar de rodar. Primeira rodada na VPS em 15/11: 1,2 milhão de linhas de treino e 4.608 células gravadas para 14/11. Parado, o container usa 47 MiB; o pico de RAM durante a rodada não foi medido.

**Rate limit atrás do túnel:** todo pedido chega na API vindo do container do `cloudflared`. Por isso o compose define `CLIENT_IP_HEADER=CF-Connecting-IP`, e a API conta os pedidos pelo IP real do usuário. Só use essa variável atrás de um proxy que sobrescreve o header. Sem proxy, qualquer cliente escolheria o próprio IP.

## Segurança da VPS

- **Docker passa por cima do `ufw`.** Uma porta em `ports:` fica aberta para a internet mesmo com o firewall bloqueando. Por isso o compose não publica nenhuma.
- Firewall: só SSH de entrada (`ufw default deny incoming`, `ufw allow OpenSSH`).
- SSH só por chave: `PasswordAuthentication no` e `PermitRootLogin no` no `sshd_config`, e `fail2ban` ligado.
- No Cloudflare, uma regra de rate limiting no WAF para `/api/v1/calendar` e `/api/v1/export`, além do limite da própria API.
- A API roda com um usuário sem privilégio dentro do container (`backend/Dockerfile`).
