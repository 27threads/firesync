# CLAUDE.md

Leia o [README.md](README.md) antes de qualquer tarefa. Ele tem a ordem de leitura dos documentos, a estrutura do repositório e as regras de harmonização que não mudam.

## Objetivo: prêmio global

A equipe quer ganhar um prêmio global do Space Apps. Leia o [docs/premiacao.md](docs/premiacao.md) antes de qualquer tarefa e siga as regras do fim dele:

- Antes de começar, diga qual dos 5 critérios (Impact, Creativity, Validity, Relevance, Presentation) a tarefa melhora. Os critérios vêm primeiro: as categorias só contam na fase final, entre os finalistas. Se a tarefa não melhora nenhum critério, avise que ela pode ficar para depois da submissão.
- Funcionando vale mais que completo. Prometa só o que foi medido.
- Dados da NASA visíveis, tudo o que o jurado vê em inglês, toda fonte externa em References.

## Antes de escrever código

- Ache sua tarefa em [docs/tarefas.md](docs/tarefas.md). Mexa só nas pastas da sua frente e trabalhe na branch dela. Atualize o status da tarefa ao começar e ao terminar.
- Confira em [docs/arquitetura.md](docs/arquitetura.md) se a stack da parte que você vai mexer já foi decidida. Se estiver "a decidir", pergunte. Não escolha linguagem, banco ou framework por conta própria.
- Os documentos em `docs/` são a fonte de verdade. Se o código e um documento discordarem, pergunte antes de mudar qualquer um dos dois.
- A abordagem de harmonização é da equipe (regra do Space Apps). Implemente o que está documentado e não invente outro método.
- Siga os "Princípios de código" de [docs/arquitetura.md](docs/arquitetura.md): **arquitetura hexagonal** na API (domínio e casos de uso no centro, portas e adaptadores em volta), **Clean Code**, contas em funções puras e transações.
- Siga o [docs/testes.md](docs/testes.md):
  - **TDD:** o teste vem antes do código. Veja o teste falhar, depois faça passar, depois refatore.
  - **Bug:** primeiro um teste que reproduz o bug e falha, depois a correção, e o teste passa. Correção sem esse teste não entra.
  - **Esteira:** rode os testes antes do PR. A esteira do GitHub Actions precisa passar.
  - **Cobertura só sobe:** se a cobertura medida passar do mínimo, suba o mínimo no mesmo PR.
  - **Sem código morto:** nada de import, variável, função ou classe sem uso, nem código comentado. A esteira roda `ruff check .` e `vulture` e quebra se achar. Rode os dois antes do PR.
  - **Especificação TDD já escrita:** se você implementar algo de `backend/tests/domain` ou `application` e o teste passar, a esteira quebra com XPASS. Tire o `xfail` daquele teste.

## Documentos

- Todo documento novo vai em `docs/`, com nome em minúsculas, sem acento e com hífen (ex.: `docs/api.md`).
- Ao criar ou renomear um documento, atualize a tabela de leitura do README.
- **Sem texto lixo nos docs.** Ao terminar uma tarefa, corrija ou apague nos `.md` o que ela tornou falso: status, pendência, "a decidir", "ainda não existe". Não deixe item riscado, pergunta já respondida nem a mesma regra copiada em vários docs: a regra fica num doc só, e os outros põem o link. Decisão com o porquê não é lixo e fica.

## Regras de código

- Tudo o que é público fica em **inglês**: interface, mensagens para o usuário, endpoints, campos do JSON, códigos de erro, arquivos de export e nomes de funções, classes e variáveis no código. Quem avalia o projeto lê inglês. Documentos internos (`docs/`) em português.
- O banco é a exceção: tabelas e colunas em português, iguais às do documento de importação (`focos`, `regioes`, `cobertura`, `fatores_harmonizacao`, `agregados`). A tradução para os nomes em inglês do contrato ([docs/api.md](docs/api.md)) acontece num lugar só, na camada da API que lê o banco.
- Nada de região fixa no código. Amazônia, Pantanal e qualquer outra região são dados em `regioes`.
- Datas e horas em UTC.
- Segredos (MAP_KEY do FIRMS, credenciais do banco) só em variáveis de ambiente. Nunca no código nem em commit.

## Dados

- Não commite CSVs descompactados nem arquivos grandes gerados pelo pipeline. Os ZIPs de teste em `data-pipeline/data/` já estão versionados.
- Para testar, use os arquivos de 2024 (Brasil, SP). O histórico completo fica só no banco de teste da frente A, fora do git ([docs/pipeline-dados.md](docs/pipeline-dados.md)).

## Git

- Nunca adicione `Co-Authored-By` (nem outra linha de coautoria ou atribuição) nas mensagens de commit. O uso de IA é registrado só na tabela "Uso de IA" do README.
- Nunca adicione "🤖 Generated with [Claude Code](https://claude.com/claude-code)" (nem outra atribuição de ferramenta) na descrição ou nos comentários de pull requests.
- **Nunca faça push numa branch cujo PR já foi mergeado.** O commit fica fora da `main` e se perde sem aviso (já aconteceu: o `alert_rules.json` 0.2 ficou na branch do PR #14). Antes de cada push, confira o PR da branch com `gh pr view --json state`. Se estiver `MERGED`, crie uma branch nova a partir da `main` atualizada e abra outro PR.
- **Nunca faça commit direto na `main`. Sempre por PR**, numa branch a partir da `main` atualizada, com a esteira verde.
- **Exceção: hotfix urgente.** Só quando o site no ar está quebrado e não dá para esperar a esteira. Só um administrador pode, porque a proteção deixa administradores passarem por cima. Depois do hotfix, abra um PR com o teste que reproduz o bug, como manda a regra dos bugs, para a correção ficar protegida.
- A `main` é protegida no GitHub: exige PR e os 5 jobs da esteira verdes.

- **Versionamento SemVer** ([docs/versionamento.md](docs/versionamento.md)): toda mensagem de commit e todo título de PR começam com o tipo (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`, `refactor:`…). Mudança que quebra o contrato leva `!` (`feat(api)!: …`). Versões só pelo workflow **Release**, nunca com tag à mão.

## Uso de IA

Toda parte gerada ou assistida por IA precisa entrar na tabela "Uso de IA" do README, no mesmo commit do código.

## Comandos

Pipeline de dados (bash, a partir de `data-pipeline/`):

- Instalar: `pip install -r requirements.txt`
- Instalar para testar: `pip install -r requirements-dev.txt`
- Testes: `python test_pipeline.py` (sem banco), `TEST_DATABASE_URL=... python test_banco.py` e `TEST_DATABASE_URL=... pytest tests` (num Postgres descartável; comandos em [docs/testes.md](docs/testes.md))
- Etapas: `python pipeline.py cadastrar|download|stage|sem_dados|importar|clean|inpe`, `python agregar.py`, `python job_nrt.py` (rodada do job NRT) e `python eda.py` (detalhes em [docs/pipeline-dados.md](docs/pipeline-dados.md))

API (a partir da raiz): `pip install -r backend/requirements-dev.txt` e `pytest backend/tests -rxX`.

Jornadas de usuário (a partir de `frontend/e2e/`): `npm ci` e `npx playwright test`.

Front (a partir de `frontend/`): `npm ci`, `npm test` (Vitest), `npm run dev` (porta 5173) e `npm run build`.

O resto da API: a preencher quando a stack estiver definida.
