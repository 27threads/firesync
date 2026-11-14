# CLAUDE.md

Leia o [README.md](README.md) antes de qualquer tarefa. Ele tem a ordem de leitura dos documentos, a estrutura do repositório e as regras de harmonização que não mudam.

## Antes de escrever código

- Ache sua tarefa em [docs/tarefas.md](docs/tarefas.md). Mexa só nas pastas da sua frente e trabalhe na branch dela. Atualize o status da tarefa ao começar e ao terminar.
- Confira em [docs/arquitetura.md](docs/arquitetura.md) se a stack da parte que você vai mexer já foi decidida. Se estiver "a decidir", pergunte. Não escolha linguagem, banco ou framework por conta própria.
- Os documentos em `docs/` são a fonte de verdade. Se o código e um documento discordarem, pergunte antes de mudar qualquer um dos dois.
- A abordagem de harmonização é da equipe (regra do Space Apps). Implemente o que está documentado e não invente outro método.

## Documentos

- Todo documento novo vai em `docs/`, com nome em minúsculas, sem acento e com hífen (ex.: `docs/api.md`).
- Ao criar ou renomear um documento, atualize a tabela de leitura do README.

## Regras de código

- Interface, textos do app e mensagens para o usuário em **inglês**. Documentos internos em português.
- Nomes de tabelas e colunas do banco iguais aos do documento de importação (`focos`, `regioes`, `cobertura`, `fatores_harmonizacao`, `agregados`).
- Nada de região fixa no código. Amazônia, Pantanal e qualquer outra região são dados em `regioes`.
- Datas e horas em UTC.
- Segredos (MAP_KEY do FIRMS, credenciais do banco) só em variáveis de ambiente. Nunca no código nem em commit.

## Dados

- Não commite CSVs descompactados nem arquivos grandes gerados pelo pipeline. Os ZIPs de teste em `data-pipeline/data/` já estão versionados.
- Para testar, use os arquivos de 2024 (Brasil, SP). O histórico completo ainda não chegou.

## Git

- Nunca adicione `Co-Authored-By` (nem outra linha de coautoria ou atribuição) nas mensagens de commit. O uso de IA é registrado só na tabela "Uso de IA" do README.

## Uso de IA

Toda parte gerada ou assistida por IA precisa entrar na tabela "Uso de IA" do README, no mesmo commit do código.

## Comandos

Pipeline de dados (bash, a partir de `data-pipeline/`):

- Instalar: `pip install -r requirements.txt`
- Testes: `python test_pipeline.py`
- Etapas: `python pipeline.py download|stage|clean` e `python eda.py` (detalhes em [docs/pipeline-dados.md](docs/pipeline-dados.md))

API e front: a preencher quando a stack estiver definida.
