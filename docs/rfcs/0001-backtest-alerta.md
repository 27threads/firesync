# RFC 0001: Backtest do nível de alerta (solução A + B)
- **Status:** Aprovado na revisão do PR #42 (Mateus). A implementação espera as perguntas em aberto da frente B
- **Autor:** Eduardo
- **Data:** 2026-11-14

Critério que melhora (ver [premiacao.md](../premiacao.md)): **Validity**. A tela de Método passa a mostrar um número medido sobre o alerta, com o limite declarado. A solução B ajuda também na **Presentation**, com a antecedência de uma crise real no vídeo.

## Contexto e problema

O nível de alerta (Normal / Atenção / Crítico) sai da regra do `config/alert_rules.json` (hoje a `0.2`), que ainda não foi calibrada. O [validacao-alerta.md](../validacao-alerta.md) define **o que** medir: teste retroativo de 2013 a 2024, gabarito "14 dias seguintes acima do P90 do normal" e ganho sobre uma regra ingênua. A revisão do Mateus no PR #42 fixou três pontos: o ganho é o número que decide, as janelas não podem se sobrepor e o texto da tela tem que dizer o que foi medido.

Este RFC define **como** implementar: arquivos, consultas, contas e testes.

## Objetivos / Não-objetivos

**Objetivos**
- `data-pipeline/validacao/backtest_alerta.py`: só **lê** o banco e gera `relatorios/alerta/backtest.csv`, `por_bioma.csv` e `eventos.csv`.
- `data-pipeline/validacao/test_backtest_alerta.py`: autoteste sem banco, com dados inventados, que termina com "OK". Inclui o caso de sobreposição das janelas.
- `data-pipeline/referencia/eventos_conhecidos.csv`: crises com data, lugar e **fonte oficial**.

**Não-objetivos**
- Escolher a `v1`. Isso é da frente B, pela tabela e pela regra de decisão do [validacao-alerta.md](../validacao-alerta.md).
- Gravar no banco, criar migration ou mudar o `alert_rules.json`.
- Área queimada (MCD64A1), que fica como próximo passo.
- Ligar o script à API. A frente C lê a `v1` do `alert_rules.json`, como já está previsto.

## Proposta

### Fluxo

```mermaid
flowchart LR
  DB[(agregados_diarios<br/>VIIRS, tipo 0)] -->|1 consulta por unidade| M[matriz unidade × dia<br/>2012-02-01..2024-12-31]
  M --> R[somas móveis<br/>7 e 14 dias]
  R --> N[normal por semana<br/>±15 dias, outros anos]
  N --> L[nível por regra da grade]
  N --> G[gabarito t+1..t+14]
  L --> C[medidas por regra]
  G --> C
  C --> O[relatorios/alerta/*.csv]
  E[eventos_conhecidos.csv] --> L
```

### 1. Leitura (única parte com banco)

Uma consulta para as unidades res 4 e uma para os biomas. O `agregados_diarios` já tem só um VIIRS por período (S-NPP de 2012-02 a 2024-12) e só `tipo = 0` ([agregar.py](../../data-pipeline/agregar.py), linhas 44 a 51), então não precisa de filtro de satélite nem de tipo.

A célula-mãe res 4 sai por conta de bits, sem extensão H3 no Postgres: troca a resolução para 4 e preenche os dígitos 5 e 6 com 7. A fórmula foi conferida contra o `h3.cell_to_parent` em 1.000 células do Brasil.

```sql
-- unidades res 4
SELECT ((h3 & ~(15::bigint << 52)) | (4::bigint << 52) | (63::bigint << 27)) AS unidade,
       data, sum(focos_brutos) AS n
FROM agregados_diarios
WHERE data >= '2012-02-01' AND data < '2025-01-01'
GROUP BY 1, 2;

-- biomas
SELECT regiao_id AS unidade, data, sum(focos_brutos) AS n
FROM agregados_diarios
WHERE data >= '2012-02-01' AND data < '2025-01-01'
GROUP BY 1, 2;
```

O resultado vira uma matriz densa `int32[unidade, dia]` com zero onde não há linha (~5 mil × 4.718 dias ≈ 95 MB). Usa `pandas` e `numpy`, que já estão no `requirements.txt`. Nenhuma dependência nova.

### 2. Contas (funções puras, sem banco)

Tudo em `numpy`, vetorizado por unidade. Para cada semana, `t` é o último dia avaliado (todo domingo de 2013-01-06 a 2024-12-15, para o gabarito caber até 2024-12-29).

| Função | Entrada → saída |
| --- | --- |
| `somas_moveis(m, k)` | matriz diária → soma dos `k` dias terminando em cada dia (`cumsum`) |
| `indices_normal(t, anos, raio=15)` | dia `t` → índices do mesmo dia do ano, deslocado de −15 a +15, **nos outros anos** (exclui o ano de `t`) |
| `normal(s, idx)` | somas móveis + índices → mediana, P75, P90 por unidade |
| `nivel(s7, s3, s3_antes, normal7, regra)` | → 0 Normal, 1 Atenção, 2 Crítico |
| `gabarito(s14_depois, p90_14, minimo=10)` | → bool "muito fogo" |
| `medidas(niveis, gabarito)` | → frequência, acerto, cobertura, alarme falso, estabilidade |
| `ingenua_mesma_frequencia(s7, normal7, gabarito, freq_alvo)` | percentil da ingênua ajustado até dar a frequência da regra → acerto |

**Janelas:** as definidas em "Janelas" no [validacao-alerta.md](../validacao-alerta.md). Na matriz de somas móveis, o nível lê `s7[t]`, a tendência compara `s3[t] > s3[t−3]` e o gabarito lê `s14[t+14]`. A soma de 14 dias que termina em `t+14` começa em `t+1`.

**Nível** (regra `0.2`, com os parâmetros vindos da grade):
- **Crítico:** `s7 ≥ razao × mediana` **e** (se a tendência estiver ligada) `s3[t] > s3[t−3]`. Com mediana zero, vale `s7 ≥ 10` (mesmo piso do gabarito; ver "Perguntas em aberto").
- **Atenção:** não é Crítico e `s7 > P75` (ou P90, conforme a grade).
- **Normal:** o resto.

**Grade:** razão em {1,5; 2; 2,5; 3} × tendência {ligada, desligada} × Atenção em {P75, P90} = 16 regras, mais a `0.2` marcada. O P90 e o piso de 10 do gabarito também rodam com {P80, P95} e {5, 20}, para mostrar a sensibilidade.

**Medidas por regra** (sobre todas as semanas × unidades):
- frequência de cada nível;
- acerto do Crítico = P(gabarito | Crítico);
- cobertura = P(Crítico ou Atenção | gabarito), e cobertura só do Crítico = P(Crítico | gabarito);
- alarme falso = 1 − acerto;
- estabilidade = trocas de nível por unidade por mês;
- **ganho** = acerto − acerto da ingênua na mesma frequência, no total e por ano (`anos_com_ganho_positivo`, de 12).

### 3. Saída

`data-pipeline/relatorios/alerta/`. Hoje `relatorios/` só está fora do git pelo `.git/info/exclude` local; o PR do script põe `data-pipeline/relatorios/` no `.gitignore`.

| Arquivo | Linhas | Colunas principais |
| --- | --- | --- |
| `backtest.csv` | 1 por regra da grade (+ sensibilidade) | `regra, razao, tendencia, atencao, p_gabarito, minimo, freq_normal, freq_atencao, freq_critico, acerto, cobertura, cobertura_critico, alarme_falso, trocas_mes, acerto_ingenua, ganho, anos_com_ganho_positivo` |
| `por_bioma.csv` | 1 por regra × bioma | as mesmas, nos 6 biomas inteiros |
| `eventos.csv` | 1 por evento × semana | `evento, semana, nivel, detections, typical_median` e a `antecedencia_semanas` |
| `relatorio.txt` | resumo | a melhor regra por ganho e se alguma passou na regra de decisão |

### 4. Eventos conhecidos (solução B)

`data-pipeline/referencia/eventos_conhecidos.csv`:

```csv
nome,regiao_id,inicio,fim,fonte_url,fonte_descricao
```

- Lugar = `regiao_id` (bioma). UF ou polígono menor ficam para depois.
- **Nenhuma linha sem `fonte_url` oficial** (INPE, decreto de emergência, relatório do governo). O script recusa linha sem fonte.
- Candidatos: Pantanal 2020, Amazônia ago/2019, Pantanal 2024 (início antecipado), Amazônia e Cerrado 2024.
- Antecedência = semanas entre a primeira semana em Atenção ou Crítico (nas 8 semanas antes do `inicio`) e o `inicio`.

### 5. Autoteste (`test_backtest_alerta.py`, sem banco)

Segue o padrão do `harmonizacao/test_validar_inpe.py`: dados inventados, `assert` e "OK" no fim.

1. **Sobreposição (pedido do Mateus):** fogo alto só em `t−6..t` e zero depois → gabarito `False`. Se a janela do gabarito incluir `t`, o teste quebra.
2. **Sem futuro no normal:** um ano com fogo enorme não entra no normal do próprio ano.
3. **Ganho zero:** série que só persiste (cada semana igual à anterior) → ganho perto de zero sobre a ingênua.
4. **Ganho positivo:** série com um sinal que antecede o fogo e que a ingênua não vê → ganho > 0.
5. **Célula-mãe:** a fórmula de bits bate com o `h3.cell_to_parent` (o `h3` já é dependência).
6. **Evento sem fonte:** linha sem `fonte_url` levanta erro.

## Alternativas consideradas

- **Área queimada (MCD64A1) como gabarito.** É independente do VIIRS, mas custa ~11 GB, conta no Earthdata e leitura de HDF4 (~5 h). Fica para depois da submissão. Meio-termo registrado: só os blocos de um evento.
- **Rodar o backtest pela API (`recent`).** Faria a conta igual à da tela, mas a API não tem código ainda e seriam milhões de chamadas. Descartado. O risco de divergência entre o script e a API fica em "Riscos".
- **Extensão `h3-pg` para a célula-mãe.** É mais legível, mas o banco não tem a extensão e instalar mexe na imagem da frente C. A conta de bits é uma linha e está testada.
- **Normal com todos os anos (inclusive o próprio).** É mais simples, mas usa o futuro e infla o acerto. Descartado.
- **Comparar com a ingênua só no P90 fixo.** Uma regra que alerta menos ganha acerto "de graça". Descartado: a ingênua roda na mesma frequência de alerta.

## Riscos e mitigação

| Risco | Mitigação |
| --- | --- |
| Acerto inflado pela persistência do fogo | O número que decide é o ganho sobre a ingênua na mesma frequência, com a regra de decisão fixada antes de rodar |
| Dia sem dado do S-NPP (falha do satélite) vira zero | Conferir a `cobertura` e listar no `relatorio.txt` os dias sem arquivo. Se houver muitos, as semanas que tocam esses dias saem do teste |
| A conta do script diverge da que a API vai fazer | O script lê os parâmetros do próprio `alert_rules.json`. Quando a frente C implementar o `recent`, um teste compara as duas contas numa unidade |
| Memória (matriz ~95 MB + somas) | `int32` e somas por bloco de unidades, se precisar |
| Mediana zero em lugares quase sem fogo | Piso de 10 detecções (ver "Perguntas em aberto") |
| Data de evento sem fonte confiável | O script recusa a linha. O evento sai da lista em vez de entrar sem fonte |

## Plano de implementação

Branch nova `a-backtest-alerta`, a partir da `main` depois do merge do PR #42 e das respostas da frente B às perguntas em aberto (precisam vir antes da rodada, não antes do merge). TDD: o teste vem antes de cada função.

0. `data-pipeline/relatorios/` no `.gitignore`.

1. **Autoteste e funções puras** (`test_backtest_alerta.py` + contas do item 2), sem banco. ~1 h.
2. **Leitura do banco e saída CSV.** Rodar no banco de teste, com o tempo e os números no PR. ~1 h.
3. **`eventos_conhecidos.csv`** com as fontes, mais o `eventos.csv` gerado. ~1 h.
4. **PR** com o `backtest.csv` colado (ou anexado), o resumo para a frente B e a linha na tabela "Uso de IA" do README. A esteira roda `ruff` e `vulture`.

## Perguntas em aberto

1. **Ganho mínimo** (frente B): qual o tamanho do ganho para a `v1` valer? O documento já fixa "positivo no total e em pelo menos 7 dos 12 anos", mas falta o valor mínimo.
2. **Definição da tendência** (frentes B e C): o `alert_rules.json` diz `trend_days: 3` e `requires_rising_trend: true`, mas não diz contra o quê. Este RFC usa "últimos 3 dias > 3 dias anteriores". A API precisa usar a mesma conta.
3. **Mediana zero** (frente B): Crítico só com `s7 ≥ 10` é aceitável, ou o lugar fica sempre Normal?
4. **Semana fixa (domingo) ou deslizante:** o RFC usa o domingo para não contar semanas sobrepostas duas vezes. Se a frente B preferir dia a dia, o custo sobe 7 vezes.
