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

Linguagem: **Python**, confirmada por Rafael para esta primeira parte. O framework HTTP continua a decidir; FastAPI é uma proposta (ver [docs/arquitetura.md](../docs/arquitetura.md), ponto 4).

## Estrutura inicial

Layout `src/` para o futuro pacote `firesync_backend`, com testes fora do código de produção. As pastas contêm apenas `.gitkeep`; ainda não há implementação nem configuração de empacotamento.

```text
backend/
├── src/firesync_backend/
│   ├── domain/
│   │   ├── models/                 objetos e valores do domínio
│   │   └── calculations/           funções puras de cálculo
│   ├── services/                   casos de uso e regras de negócio
│   ├── repositories/
│   │   ├── interfaces/             contratos de acesso aos dados
│   │   └── postgres/               SQL e tradução dos nomes do banco
│   ├── api/
│   │   ├── routes/                 entrada e saída HTTP
│   │   └── schemas/                validação e serialização do contrato
│   └── config/                     leitura e validação de configuração
├── tests/
│   ├── unit/
│   │   ├── domain/                 cálculos e objetos do domínio
│   │   └── services/               regras com repositórios falsos
│   ├── integration/repositories/   acesso real ao PostgreSQL/PostGIS
│   ├── contract/api/               formatos públicos de pedidos e respostas
│   ├── fixtures/                  dados pequenos para testes
│   └── fakes/                     implementações falsas dos contratos
└── data/                          espaço reservado para dados locais
```

Os serviços recebem os contratos de repositório por injeção de dependência. O domínio e os serviços permanecem independentes do framework HTTP e do driver SQL. As rotas delegam aos serviços; os repositórios concretos implementam os contratos e concentram o SQL. A configuração conecta as implementações aos serviços na inicialização.

As regras de alerta continuam em `config/alert_rules.json` na raiz do repositório. Dados reais, segredos e exports gerados não devem ser commitados em `backend/data/`. Os dados pequenos e versionados dos testes ficam em `tests/fixtures/`.

A separação permite testar e alterar as camadas de forma independente. Desempenho e capacidade de escala serão medidos quando houver implementação e consultas reais.

## Commits

Na branch `dev-backend-rafael`, cada classe de produção ou de teste terá seu próprio commit, usando Conventional Commits com descrição em português. A criação inicial de pastas fica em um único commit, pois ainda não há classes.
