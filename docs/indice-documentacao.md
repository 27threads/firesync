# Índice da documentação

Leia nesta ordem antes de escrever código. Os documentos são a fonte de verdade. Se o código e um documento discordarem, pergunte antes de mudar qualquer um dos dois.

| # | Documento | O que define | Quando ler |
| --- | --- | --- | --- |
| 1 | [Requisitos](requisitos.md) | O que o desafio exige (RF), o que dá pontos (RD), requisitos não funcionais e checklist da submissão | Sempre |
| 2 | [FIRMS — extração e dados disponíveis](firms-extracao-dados.md) | Sensores, datas, formas de baixar (arquivo, API, WMS), colunas dos CSVs | Antes de mexer em importação ou API do FIRMS |
| 3 | [Plano de extração — Brasil (Amazônia)](plano-extracao-amazonia.md) | Quais dados baixar, papel de cada satélite, dados de validação (IBGE, INPE), jobs de atualização | Antes de mexer no pipeline |
| 4 | [Importação de novas regiões](importacao-regioes.md) | Importador, tabelas, chave única, fatores de harmonização por região, como adicionar região | Antes de mexer no banco, no pipeline ou na API |
| 5 | [Arquitetura e stack](arquitetura.md) | Stack de cada componente, o que já está decidido e o que falta decidir | Antes de escrever qualquer código |
| 6 | [Tarefas](tarefas.md) | Frentes, responsáveis, branches, pastas de cada um, marcos e status | Antes de começar qualquer tarefa |
| 7 | [Pipeline de dados — o que já foi feito](pipeline-dados.md) | Download do histórico, filtros de qualidade, análise por satélite, achados | Antes de mexer em `data-pipeline/` |
| 8 | [Banco de dados — decisões para o backend](banco.md) | Imagem, H3, resolução, schema, consulta da API, carga na VPS, benchmark | Antes de mexer no banco ou na API |
| 9 | [Contrato da API](api.md) | Endpoints, pedido, resposta, erros, export de auditoria. JSON de exemplo em [api-exemplo.json](api-exemplo.json) | Antes de mexer na API ou no front |
| 10 | [Prompt do frontend](prompt-frontend.md) | Prompt para o agente que constrói o front: direção de design, regras de dado na tela, animação, performance e etapas de construção | Antes de começar a frente D |
| 11 | [Critérios de julgamento e prêmios](premiacao.md) | Os 5 critérios, as categorias-alvo e as regras de prioridade da equipe | Antes de qualquer tarefa |
| 12 | [Decisões da harmonização](decisoes-harmonizacao.md) | Fator Aqua → S-NPP, faixa P5–P95, resultado da calibração e limites a declarar no Método | Antes de mexer em calibração, agregação ou na conta da API |
| 13 | [Regras entre as variáveis](regras-variaveis.md) | Colunas de cada sensor, regras de remoção e de duplicata, classificador complementar | Antes de mexer nos filtros do pipeline |
| 14 | [UX: racional das telas](ux-telas.md) | Objetivo, tarefas e decisões do usuário em cada tela | Antes de mexer no front |
| 15 | [Pitch e vídeo](pitch.md) | Roteiro de 30 s, legenda em inglês e como gravar | Antes de montar a demo |
| 16 | [Testes e esteira](testes.md) | TDD, regra dos bugs, cobertura, jornadas e jobs do GitHub Actions | Antes de escrever código |
| 17 | [Versionamento (SemVer)](versionamento.md) | Tipo no commit e no título do PR, como lançar uma versão | Antes do primeiro commit |
| 18 | [Validação do nível de alerta](validacao-alerta.md) | Solução A + B da issue #9: teste retroativo com "o que veio depois" e eventos conhecidos, no lugar da área queimada | Antes de mexer no alerta ou no `alert_rules.json` |
| 19 | [RFC 0001: backtest do alerta](rfcs/0001-backtest-alerta.md) | Como implementar a solução A + B: consultas, janelas, contas, saídas, autoteste e plano | Antes de implementar o backtest do alerta |
| 20 | [Validação da API com a carga real](validacao-api-eduardo.md) | Roteiro para o Eduardo conferir números, cobertura, ZIP e latência antes de fechar D7/M2 | Ao integrar a API com a carga real |
| 21 | [Simulação e auditoria pelos logs](simulacao.md) | Como rodar o sistema de ponta a ponta num banco descartável e auditar pelos logs se ele entrega o que os critérios cobram | Antes de rodar a simulação ou investigar um problema |
| 22 | [Restrições para o mundo](escala-mundial.md) | O que muda quando a cobertura passar do Brasil para o mundo, com a saída proposta para cada ponto | Antes de mexer em cobertura, seleção de área ou camada de focos |
| 23 | [Deploy](deploy.md) | Front no Cloudflare, banco/API/job NRT na VPS pelo Cloudflare Tunnel, variáveis e segurança da VPS | Antes de publicar ou mexer em `infra/` |
| 24 | [Página do projeto](pagina-projeto.md) | Texto em inglês de cada campo da página do projeto no Space Apps (C9) | Antes de preencher ou mudar a página da submissão |
| 25 | [RFC 0004: assistente virtual](rfcs/0004-assistente-virtual.md) | Chat no site que responde perguntas com tool-use sobre os casos de uso da API: ferramentas, contrato `/ask`, front, riscos e plano | Antes de mexer no assistente |

Regras para agentes: [CLAUDE.md](../CLAUDE.md).
