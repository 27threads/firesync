# Testes e esteira

Nov 14, 2026 · vale para todo código do projeto

## Regras

1. **TDD em todo o desenvolvimento.** O teste vem antes do código: escreva o teste, veja ele falhar (vermelho), escreva o mínimo de código para ele passar (verde) e melhore o código com o teste passando (refatorar).
2. **Todo bug ganha um teste antes da correção.** Encontrou um bug: escreva um teste que reproduz o bug e **falha**. Corrija. O teste passa e fica no repositório para o bug nunca voltar. Um PR de correção sem esse teste não entra.
3. **Todo PR com código roda a esteira** e só entra na `main` se ela passar (RNF08).
4. **A cobertura só sobe.** O mínimo fica no arquivo de configuração. Quando a cobertura medida passar do mínimo, suba o mínimo no mesmo PR.
5. **Testes testam comportamento, não implementação.** Entrada e saída pela interface pública. Nada de testar função privada ou contar chamadas internas. Assim dá para refatorar sem quebrar teste.
6. **Sem código morto.** Import, variável, função ou classe sem uso, e código comentado, não entram. A esteira checa com o `ruff` (regras F, configuradas no `ruff.toml`) e com o `vulture`. Se for um falso positivo, ignore só aquela linha (`# noqa: <regra>`) e escreva o motivo. No front, quando existir, o mesmo vale com `noUnusedLocals` e `noUnusedParameters` no TypeScript.
7. **A `main` é protegida.** Só entra por PR e só com todos os jobs da esteira verdes.

## Tipos de teste

| Tipo | O que testa | Onde | Velocidade | Precisa de |
| --- | --- | --- | --- | --- |
| **Unidade** | Regras puras: filtros, faixa P5–P95, origem do mês, intensidade, alerta, janelas | `data-pipeline/test_pipeline.py`, `backend/tests/domain/` | milissegundos | nada |
| **Caso de uso** | A aplicação com adaptadores falsos nas portas (arquitetura hexagonal) | `backend/tests/application/` | milissegundos | nada |
| **Contrato** | O `api-exemplo.json` e o `alert_rules.json` seguem as regras do `api.md` | `backend/tests/contract/` | milissegundos | nada |
| **Integração** | O código com um Postgres de verdade: importação, SP substituindo NRT, agregação, job NRT com o FIRMS simulado | `data-pipeline/test_banco.py`, `data-pipeline/tests/` | segundos | PostGIS (Docker) |
| **Jornada de usuário (E2E)** | O site inteiro, do jeito que o usuário usa: escolher área, ver calendário, alerta, export | `frontend/e2e/` | segundos por jornada | navegador (Playwright) |

**Proporção:** muitos testes de unidade, alguns de integração e poucas jornadas. As jornadas são lentas e, quando falham, não dizem onde está o erro. A unidade diz na hora.

### Testes de unidade ou caixa-preta?

Os dois, com papéis diferentes. **Não vale trocar os testes de unidade por caixa-preta.**

- Os testes de unidade daqui **já são caixa-preta no nível da função**: chamam a função pública com uma entrada e conferem a saída, sem olhar a implementação. O que não pode é teste caixa-branca, preso aos detalhes internos, porque ele quebra a cada refatoração.
- Só com caixa-preta do sistema inteiro (as jornadas), cada caso de borda vira uma jornada lenta: 29 de fevereiro, 13 cenários, pixel saturado do MODIS. Elas também precisam do site, da API e do banco no ar, e quando falham não dizem qual regra quebrou.
- As jornadas garantem que as peças funcionam juntas. A unidade garante que cada regra está certa.

## TDD na prática: testes que vêm antes do código

A API e o front ainda não existem, mas os testes deles já estão no repositório:

- **`backend/tests/domain/` e `backend/tests/application/`:** a especificação do núcleo da API (faixa P5–P95, origem e satélite do mês, intensidade, alerta, janelas, IDs H3, calendário). Os valores foram calculados à mão. Cada teste tem `xfail(strict=True)`: enquanto o código não existe, ele falha e a esteira aceita. **Quando o código fizer o teste passar, a esteira quebra com XPASS.** É o sinal para tirar o `xfail` daquele teste, que a partir daí vale de verdade.
- **`frontend/e2e/jornadas.spec.ts`:** 9 jornadas, cada uma com `test.fixme`. Quem fizer a tela tira o `fixme` da jornada dela.

### Jornadas de usuário

| # | Jornada | Requisito |
| --- | --- | --- |
| J1 | Escolhe uma região pronta e vê o calendário de 2003 até hoje, com o crédito ao FIRMS | RF06, RF08 |
| J2 | Desenha uma área no mapa e recebe o calendário dela | RD01 |
| J3 | Digita latitude, longitude e raio | RD02 |
| J4 | Área fora da cobertura mostra aviso, nunca um calendário de zeros | contrato |
| J5 | Vê os últimos 7 dias contra o normal da época, com a hora da atualização | RF11, RD07 |
| J6 | Mês estimado mostra a faixa de incerteza, e o mês incompleto vem marcado | RD03, contrato |
| J7 | Baixa o pacote de auditoria | RF13 |
| J8 | Dado com mais de 6 h mostra aviso de desatualizado | RNF07 |
| J9 | Muitos pedidos seguidos mostram aviso amigável, não erro | RNF06 |

Cada jornada roda no desktop e no celular. Os seletores usam papéis e textos acessíveis (`getByRole`, `getByLabel`), o que também cobra a acessibilidade (RD04, RNF05).

## Cobertura de linhas

| Parte | Medida | Mínimo | Onde fica o mínimo |
| --- | --- | --- | --- |
| `data-pipeline/` | Linhas e ramos, juntando unidade e integração | **56%**, o medido na primeira esteira (PR #24): `agregar.py` 80%, `job_nrt.py` 85%, `pipeline.py` 51% | `data-pipeline/.coveragerc` |
| `backend/src/` | Linhas e ramos | **90%**, a partir do primeiro código | `.github/workflows/ci.yml` |

O `eda.py` (análise exploratória) fica fora da cobertura. Download, `stage`, `clean` e `cadastrar` dependem do FIRMS e do IBGE, e são as próximas partes a ganhar teste.

## A esteira (GitHub Actions)

Arquivo: `.github/workflows/ci.yml`. Roda em todo PR e em todo push na `main`.

**PR só de documentação.** Se todos os arquivos mudados no PR terminam em `.md`, os jobs de teste são pulados (aparecem como "skipped", que a proteção da `main` aceita). Nenhum teste lê `.md`. Basta um arquivo de outro tipo para tudo rodar, inclusive o `docs/api-exemplo.json`, que o contrato testa. Push na `main` sempre roda tudo. Quem decide é o `.github/scripts/roda_testes.sh`, testado pelo `test_roda_testes.sh`. Não troque isso por `paths-ignore` no gatilho: sem o workflow rodar, os checks obrigatórios ficam esperando e o PR trava.

| Job | O que roda |
| --- | --- |
| **Só documentação?** | Testa o filtro e decide se os outros jobs rodam |
| **Código morto** | `ruff check .` (imports, variáveis e redefinições sem uso) e `vulture` (funções, classes e variáveis nunca usadas), fora dos testes |
| **Pipeline · unidade** | `test_pipeline.py` |
| **Pipeline · integração com PostGIS** | Migrations aplicadas duas vezes (precisam rodar de novo sem erro), `test_banco.py`, job NRT com o FIRMS simulado e o relatório de cobertura, que aparece no resumo do job |
| **API · contrato e especificação TDD** | Contrato do `api-exemplo.json` e do `alert_rules.json`, mais a especificação do domínio. Com código em `backend/src/`, também a cobertura de 90% |
| **Front · jornadas de usuário** | As jornadas compilam. Com o front criado (`frontend/package.json`), sobe o site e roda as jornadas no Chromium |

## Como rodar no seu computador

```bash
# pipeline: unidade
cd data-pipeline && pip install -r requirements-dev.txt && python test_pipeline.py
```

```bash
# pipeline: integração (precisa de Docker)
docker run -d --rm --name firesync-db-teste -e POSTGRES_PASSWORD=teste -e POSTGRES_DB=firesync_teste -p 5434:5432 postgis/postgis:16-3.4
```

```bash
cd data-pipeline && TEST_DATABASE_URL=postgresql://postgres:teste@localhost:5434/firesync_teste python test_banco.py
```

```bash
# API: contrato e especificação TDD
pip install -r backend/requirements-dev.txt && pytest backend/tests -rxX
```

```bash
# jornadas: listar (e rodar, quando o front existir)
cd frontend/e2e && npm ci && npx playwright test --list
```

O teste do job NRT (`data-pipeline/tests/`) precisa de um banco próprio, com "teste" no nome, porque apaga as tabelas.

```bash
# código morto (a partir da raiz)
pip install ruff vulture && ruff check . && vulture data-pipeline --exclude "tests,test_*.py" --min-confidence 60
```
