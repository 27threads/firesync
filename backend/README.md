# backend

API que serve o calendário, a janela recente, a camada de focos e o pacote de auditoria para o front.

- **Frente responsável:** C
- **Contrato:** [docs/api.md](../docs/api.md). Mudar o contrato exige avisar a equipe antes.
- **Lê do banco:** `config`, `regioes`, `celula_regiao`, `cobertura`, `fatores_harmonizacao`, `agregados`, `agregados_diarios`, `dias_sem_dados` e `focos` ([docs/banco.md](../docs/banco.md)).
- **Lê da configuração:** [config/alert_rules.json](../config/alert_rules.json) (alerta e classe de intensidade).
- **Não grava nada no banco.** Quem grava é o `data-pipeline/`.

Regras que valem aqui:

- Endpoints, campos do JSON, códigos de erro e nomes no código em inglês. A tradução dos nomes do banco (em português) acontece num lugar só, na camada que lê o banco.
- IDs H3 saem sempre como texto, nunca como número.
- A resolução H3 vem da tabela `config`. A API não sobe se ela não bater com as células do banco.

Ainda a decidir: linguagem e framework (proposta: Python + FastAPI, ver [docs/arquitetura.md](../docs/arquitetura.md), ponto 4).
