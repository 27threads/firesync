# config

Regras que podem mudar sem mudar o código. A API lê estes arquivos ao subir.

| Arquivo | O que é | Quem edita |
| --- | --- | --- |
| `alert_rules.json` | Regra do nível de alerta (Normal / Atenção / Crítico), janela do normal e limites da classe de intensidade | Frente B propõe, a equipe aprova |

Regras que valem aqui:

- **Todo arquivo tem `version`.** Mudou uma regra, sobe a versão. A API devolve a versão junto com o resultado, e o pacote de auditoria registra a versão usada.
- **Os valores são escolha da equipe**, a calibrar com dados. O teste retroativo que vai escolher a regra está na issue #9.
- Nada de segredo aqui. Segredo fica no `.env` (ver `infra/`).
