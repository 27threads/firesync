# Versionamento (SemVer)

Nov 14, 2026

O projeto segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/): **`MAJOR.MINOR.PATCH`**, com a tag `vX.Y.Z` e uma release no GitHub para cada versão.

## Como a versão sobe

A versão é calculada pelo **tipo** no começo das mensagens de commit, desde a última tag:

| Tipo do commit | Sobe | Exemplo |
| --- | --- | --- |
| `fix:` ou `perf:` | **PATCH** (0.1.0 → 0.1.1) | `fix(api): faixa anual somava percentis` |
| `feat:` | **MINOR** (0.1.0 → 0.2.0) | `feat(front): calendário em heatmap` |
| `tipo!:` ou `BREAKING CHANGE:` no corpo | **MAJOR** (1.2.0 → 2.0.0) | `feat(api)!: troca p10/p90 por band_low/band_high` |
| `docs:`, `test:`, `ci:`, `chore:`, `refactor:`, `style:`, `build:` | nada | `docs: atualiza o README` |

**Fase 0.y.z:** enquanto o projeto está antes do 1.0.0, uma mudança que quebra sobe o MINOR, não o MAJOR. Nessa fase, tudo ainda pode mudar.

## Marcos

| Versão | Quando | O que é |
| --- | --- | --- |
| **v0.1.0** | 14/11/2026 | Ponto de partida: documentação, contrato da API, banco, pipeline, testes e esteira |
| **v1.0.0** | Envio da submissão (domingo, 15/11) | A versão que os jurados avaliam. O link do repositório na página do projeto aponta para esta tag |

## Como lançar uma versão

Na aba **Actions** do GitHub, workflow **Release**, botão **Run workflow**:

- **`auto`** (padrão): calcula pelos commits. Se só houver `docs`, `test`, `chore` e parecidos, não lança nada e avisa.
- **`patch`**, **`minor`** ou **`major`**: força o tipo. Use **`major`** para o **1.0.0** da submissão.

O workflow testa o cálculo, cria a tag `vX.Y.Z` e a release com as notas geradas a partir dos PRs. Ele **não faz commit na `main`**, que é protegida. A versão vive na tag e na release, e o histórico de mudanças é a [página de Releases](https://github.com/27threads/firesync/releases).

## Regras

1. **Todo commit e todo título de PR começam com o tipo**, no formato `tipo(escopo opcional): descrição`. A esteira confere o título do PR (job "Título do PR no padrão").
2. **Mudança que quebra o contrato leva `!`** depois do tipo, ou `BREAKING CHANGE:` no corpo do commit. Exemplo: renomear um campo da API.
3. **Só lança versão da `main`**, nunca de outra branch.
4. **Não crie tag à mão.** Use o workflow, que testa o cálculo antes.

## O que tem versão própria

A versão do projeto não substitui estas, que continuam separadas:

| O quê | Versão | Quando muda |
| --- | --- | --- |
| Contrato da API | `/api/v1` no caminho | Só quando uma mudança quebrar o front (vira `/api/v2`) |
| Regra do alerta | `version` no `config/alert_rules.json` | A cada mudança na regra |
| Dados | `updated_at` (`config.atualizado_em`) | A cada atualização do job NRT ou da calibração |
