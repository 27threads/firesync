# Deploy

Nov 15, 2026 · frente C · decisão 12 de [arquitetura.md](arquitetura.md)

O front fica no Cloudflare. Banco, API e job NRT ficam na VPS, com `docker compose`. A VPS não abre nenhuma porta para a internet: o único caminho de fora para dentro é o Cloudflare Tunnel até a API.

```
navegador ──> Cloudflare (front estático, firesync.<conta>.workers.dev)
navegador ──> Cloudflare (api.<domínio>) ──túnel──> VPS: api ──> db
                                                    VPS: job-nrt ──> FIRMS
```

**Por que assim:** o front é só arquivo estático e fica mais rápido na CDN do Cloudflare para o jurado em qualquer país. Com o túnel, o IP da VPS não aparece, o HTTPS vem pronto e não existe porta aberta para atacar.

## Front no Cloudflare (Workers, só arquivos estáticos)

O repositório é um monorepo. O Cloudflare clona o repo inteiro e faz o build a partir de `frontend/`. O `frontend/wrangler.jsonc` diz para o `wrangler deploy` publicar o `dist/` e responder `index.html` em qualquer rota. Sem esse arquivo, o wrangler tenta se configurar sozinho e falha com Vite 5.

Em **Workers & Pages → firesync → Settings → Build**:

| Campo | Valor |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm run build` (o Cloudflare já roda `npm ci` antes) |
| Deploy command | `npx wrangler deploy` |
| Build watch paths | `frontend/*` e `docs/api-exemplo.json` (o `App.tsx` importa esse JSON) |
| Build variable | `VITE_API_URL=https://api.<domínio>` |

- O `VITE_API_URL` é uma variável de **build**, não de runtime: ela entra no JavaScript na hora do `vite build`. Mudou o valor, faça um novo deploy.
- Toda variável `VITE_` fica pública no JavaScript. Segredo nunca vai em `VITE_`.
- Os headers de segurança (CSP, HSTS, `nosniff`) ficam em `frontend/public/_headers`. Uma origem nova no front (outro servidor de tiles, por exemplo) precisa entrar no CSP desse arquivo.

## Banco, API e job NRT na VPS

Tudo em [`infra/docker-compose.yml`](../infra/docker-compose.yml). Nenhum serviço tem `ports:`.

1. Copie `infra/.env.example` para `infra/.env` e preencha. O `.env` nunca vai para o git.
2. No Cloudflare, em **Zero Trust → Networks → Tunnels**, crie um túnel, copie o token para `CLOUDFLARE_TUNNEL_TOKEN` e adicione o public hostname `api.<domínio>` → `http://api:8000`.
3. `FRONTEND_ORIGIN` é a origem exata do front, sem barra no fim. É a única que o CORS aceita.
4. Na VPS, a partir de `infra/`: `docker compose up -d --build`. A carga do banco segue o roteiro de [banco.md](banco.md#carga-na-vps-roteiro).

**Rate limit atrás do túnel:** todo pedido chega na API vindo do container do `cloudflared`. Por isso o compose define `CLIENT_IP_HEADER=CF-Connecting-IP`, e a API conta os pedidos pelo IP real do usuário. Só use essa variável atrás de um proxy que sobrescreve o header. Sem proxy, qualquer cliente escolheria o próprio IP.

## Segurança da VPS

- **Docker passa por cima do `ufw`.** Uma porta em `ports:` fica aberta para a internet mesmo com o firewall bloqueando. Por isso o compose não publica nenhuma.
- Firewall: só SSH de entrada (`ufw default deny incoming`, `ufw allow OpenSSH`).
- SSH só por chave: `PasswordAuthentication no` e `PermitRootLogin no` no `sshd_config`, e `fail2ban` ligado.
- No Cloudflare, uma regra de rate limiting no WAF para `/api/v1/calendar` e `/api/v1/export`, além do limite da própria API.
- A API roda com um usuário sem privilégio dentro do container (`backend/Dockerfile`).
