# Tarefas

Divisão do trabalho entre as 4 pessoas da equipe, até a submissão (domingo, 15/11/2026, 23h59).

## Como usar

- Cada pessoa tem uma frente e mexe **só nas pastas da sua frente**. Para mexer em outra pasta, fale antes com o responsável dela.
- As frentes dependem de **contratos** (formato da tabela `agregados` e `docs/api.md`), nunca do código de outra frente. Até a parte real ficar pronta, trabalhe com dados falsos no formato do contrato.
- Cada pessoa trabalha na branch da sua frente e faz merge na `main` assim que algo funcionar.
- Mudar um contrato exige avisar a equipe antes. Depois, atualize o documento do contrato no mesmo commit.
- Ao começar uma tarefa, mude o status para `fazendo`. Ao terminar, mude para `feito`. Status possíveis: `a fazer`, `fazendo`, `feito`, `bloqueado`, `cortado`.
- Agentes: leia a sua frente inteira e os documentos indicados nela antes de começar.

## Frentes

| Frente | Responsável | Branch | Pastas |
| --- | --- | --- | --- |
| A. Importador e dados | | `a-importador` | `data-pipeline/` (importação) |
| B. Harmonização | | `b-harmonizacao` | `data-pipeline/` (calibração e agregação, em módulo separado do importador) |
| C. API, deploy e submissão | | `c-api` | `backend/`, configuração de deploy, `docs/api.md` |
| D. Frontend e demo | | `d-frontend` | `frontend/` |

A e B dividem `data-pipeline/`. Antes de começar, combinem a estrutura de subpastas para não editarem os mesmos arquivos.

## Marcos

| Marco | Quando | O que precisa estar pronto |
| --- | --- | --- |
| M0. Contratos | Sábado, antes de dividir | Stack decidida, formato de `agregados`, `docs/api.md` com JSON de exemplo |
| M1. Partes isoladas | Sábado, fim do dia | Importador com os dados de 2024, fatores calculados, API respondendo com dados falsos, front mostrando o calendário com o JSON de exemplo |
| M2. Integração | Domingo, 12h | Front → API → `agregados` reais, rodando local de ponta a ponta |
| M3. No ar | Domingo, 18h | App público, sem login, interface em inglês |
| M4. Submissão | Domingo, 22h | Página e demo enviadas. Fica uma folga até 23h59 para reenvio |

## M0. Contratos (todos juntos)

| ID | Tarefa | Status | Pronto quando |
| --- | --- | --- | --- |
| T00 | Decidir os pontos 1, 2, 4, 5 e 12 de [arquitetura.md](arquitetura.md) e escrever as justificativas | a fazer | Os 5 pontos preenchidos |
| T01 | Fechar o formato de `agregados` (colunas, tipos, resolução H3) | a fazer | Seção escrita em [importacao-regioes.md](importacao-regioes.md) |
| T02 | Escrever `docs/api.md` com endpoints, pedido, resposta, erros e um JSON de exemplo | fazendo (rascunho na branch `c-api`, falta A e D lerem) | A e D leram e concordaram |
| T03 | Preencher responsáveis desta página e criar as 4 branches | a fazer | Tabela de frentes preenchida |

## A. Importador e dados

Ler antes: [firms-extracao-dados.md](firms-extracao-dados.md), [plano-extracao-amazonia.md](plano-extracao-amazonia.md), [importacao-regioes.md](importacao-regioes.md).

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| A1 | Conferir o pedido do FIRMS. Se o histórico não chegar a tempo, baixar os resumos anuais por país (Brasil, 2003 até hoje), que não passam por aprovação | — | feito (resumos anuais 2000–2025 + API para 2026, ver [pipeline-dados.md](pipeline-dados.md)) | Histórico em mãos, ou decisão registrada de demo só com 2024 |
| A2 | Baixar o shapefile de biomas do IBGE e a série mensal do bioma Amazônia do INPE | — | fazendo (IBGE feito, falta INPE) | Arquivos em `data-pipeline/data/`, fora do git se forem grandes |
| A3 | Criar `.gitignore` para CSVs descompactados e arquivos gerados | — | feito | `git status` limpo depois de descompactar os ZIPs |
| A4 | Criar o banco com as tabelas `focos`, `regioes` e `cobertura` | T00 | feito (`data-pipeline/migrations/001_inicial.sql`, em PR) | Script de criação versionado |
| A5 | Importador: normalizar colunas, calcular H3, upsert com a chave única, atualizar `cobertura` | A4 | a fazer | `importar` carrega os 5 arquivos de 2024 e as contagens batem com a tabela do plano de extração |
| A6 | Cadastrar as regiões Amazônia e Pantanal em `regioes`, com as células em `celula_regiao` | A2, A4 | feito (os 6 biomas, `pipeline.py cadastrar`) | As duas regiões com polígono e células |
| A7 | Carregar o histórico completo | A1, A5 | a fazer | `cobertura` mostra cada satélite no período esperado |

## B. Harmonização

Ler antes: [importacao-regioes.md](importacao-regioes.md) (seção "Harmonização por região"), [plano-extracao-amazonia.md](plano-extracao-amazonia.md).

B1 e B2 podem começar direto nos CSVs de 2024, sem esperar o importador.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| B1 | Protótipo do cálculo do fator Aqua → S-NPP (escala VIIRS) **por bioma, mês e dia/noite**, em contagens por célula H3, só confiança nominal ou alta e `type = 0`. Primeiro nos CSVs de 2024, depois nos anos de sobreposição disponíveis. Ver [decisoes-harmonizacao.md](decisoes-harmonizacao.md) | — | a fazer | Fatores da Amazônia calculados, com razão média perto de 6 e variação mensal visível |
| B2 | Definir a escolha do satélite por mês (Aqua, S-NPP, NOAA-20), como aplicar a cadeia de fatores e como rotular cada mês como observado ou estimado | — | a fazer | Regra escrita em [importacao-regioes.md](importacao-regioes.md) |
| B3 | Job de calibração gravando em `fatores_harmonizacao`, com um cenário por ano de calibração (base 2012 a 2024; o próprio job roda a validação deixando um ano de fora e aplica o critério de 1,5× para escolher os anos) e só confiança nominal e alta | A5, B1 | a fazer | Fatores dos 6 biomas no banco |
| B4 | Job de agregação gravando a contagem bruta em `agregados` (célula × ano × mês × satélite × dia/noite), só do satélite que vale em cada mês e só com confiança nominal e alta, no formato do `banco.md` (PR #2) | T01, B3 | feito pela frente A (`data-pipeline/agregar.py`, PR #2) | `agregados` preenchida para as duas regiões |
| B5 | Comando `recalcular <regiao>` (fatores + agregados da região) | B3, B4 | a fazer | Rodar duas vezes dá o mesmo resultado |
| B6 | Validar a série harmonizada contra a do INPE (só forma da curva, anos altos, meses de pico) e registrar o resultado da validação do B3 (erro por ano, decisão dos anos e cobertura da faixa) | A2, A7, B4 | a fazer | Gráficos de comparação salvos, para usar na página do projeto |

## C. API, deploy e submissão

Ler antes: [requisitos.md](requisitos.md), [importacao-regioes.md](importacao-regioes.md), `docs/api.md`.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| C1 | Esqueleto da API respondendo o JSON de exemplo do `api.md` | T00, T02 | a fazer | D consegue apontar o front para ela |
| C2 | Gerar `agregados` falsos no formato do contrato, para testar sem esperar B | T01 | a fazer | Script versionado |
| C3 | Converter a área (polígono, retângulo ou lat/lon) em células H3 e somar os `agregados` | C1 | a fazer | Calendário meses × anos correto para uma área de teste |
| C4 | Sazonalidade, ranking de anos, mediana do mês atual e anomalias (RF09–RF12) | C3 | a fazer | Valores conferidos à mão para uma área |
| C5 | Resposta "sem dados" fora da `cobertura` e marcação dos dias de `dias_sem_dados` | C3 | a fazer | Área fora do Brasil devolve o aviso, não um calendário vazio |
| C6 | Export CSV dos focos da busca (RD05) | C3 | a fazer | Arquivo abre no Excel |
| C7 | Deploy público de banco, API e front | T00, M2 | a fazer | Link funciona numa janela anônima |
| C8 | Pedir a classificação FortiGuard do site | C7 | a fazer | Pedido enviado |
| C9 | Página do projeto em inglês: summary, descrição detalhada, NASA Data, referências, uso de IA | B6 | a fazer | Todos os campos do checklist de [requisitos.md](requisitos.md) preenchidos |
| C10 | Completar a tabela "Uso de IA" do README | — | a fazer | Cada parte com IA registrada |

## D. Frontend e demo

Ler antes: [requisitos.md](requisitos.md), `docs/api.md`.

D1 a D5 começam com o JSON de exemplo do `api.md`, sem esperar a API.

| ID | Tarefa | Depende de | Status | Pronto quando |
| --- | --- | --- | --- | --- |
| D1 | Esqueleto do app, interface em inglês e crédito ao FIRMS visível | T00 | a fazer | App abre local |
| D2 | Mapa com desenho de polígono e retângulo (RD01) e entrada de lat/lon (RD02) | D1 | a fazer | Área desenhada vira o pedido do `api.md` |
| D3 | Seletor de intervalo de datas (RF07) | D1 | a fazer | Datas entram no pedido |
| D4 | Calendário meses × anos em heatmap com paleta acessível (RF08, RD03, RD04) e meses com falha de satélite (`dias_sem_dados`) diferentes de zero | D1 | a fazer | Renderiza o JSON de exemplo |
| D5 | Indicadores principais, sazonalidade, ranking de anos, mês atual vs. mediana e anomalia (RF09–RF12, RD06) | D1 | a fazer | Renderiza o JSON de exemplo |
| D6 | Download das análises e do CSV (RF13, RD05) | D4, D5 | a fazer | Arquivos baixam e abrem |
| D7 | Ligar o front na API real | C3, D2–D5 | a fazer | M2 atingido |
| D8 | Demo: vídeo de até 30 s com legenda em inglês, ou até 7 slides em inglês, com nome da equipe, membros, desafio, imagem do projeto, experiência do usuário e uso dos dados da NASA | D7 | a fazer | Link público testado numa janela anônima |

## Cortado ou depois da submissão

| ID | Tarefa | Motivo |
| --- | --- | --- |
| X1 | Job de atualização NRT pela API do FIRMS | Não cabe no prazo. A demo usa dados carregados uma vez |
| X2 | Recarga SP mensal | Depende do X1 |
| X3 | Região da Califórnia | Precisa de pedido novo no FIRMS |
