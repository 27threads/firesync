# RFC 0002: Modelo A, a chance de o MODIS ver um fogo do VIIRS (caminho C)

- **Status:** Decidido pelo Weberson em 14/11/2026 (caminho C). Em revisão neste PR
- **Autor:** Weberson (frente B)
- **Data:** 2026-11-14

Critérios que melhora (ver [premiacao.md](../premiacao.md)): **Validity** e **Creativity**. A tela de Método ganha uma explicação visual de por que a harmonização é necessária e uma segunda prova, independente, de que o fator de conversão está certo. Categoria-alvo: Best Use of Science.

## Contexto e problema

A série do calendário já é harmonizada pelo **fator por contagens** (bioma × mês × dia ou noite, um cenário por ano), validado deixando um ano de fora: erro de cerca de 6% por ano na Amazônia e faixa que acerta cerca de 8 em 10 vezes ([decisoes-harmonizacao.md](../decisoes-harmonizacao.md), seção 4).

O **modelo A** era o plano original da frente B: um modelo treinado que aprende a chance de o MODIS ver cada fogo que o VIIRS viu. Na revisão do PR #1 ele passou a ser análise complementar, e o Weberson decidiu agora que ele **é entrega**, pelo caminho C abaixo.

## O que o modelo faz e o que ele não faz

- **Aprende:** a chance de o MODIS (Aqua) ter visto um fogo detectado pelo VIIRS (S-NPP), a partir de pistas do fogo: potência (FRP), temperatura, confiança, dia ou noite, mês, bioma e o tamanho do pixel do MODIS naquela passagem.
- **Não substitui o fator da série de 2003 a 2011.** Para aplicar o modelo a um fogo antigo, seria preciso a potência de cada fogo que o MODIS **não viu**, e esses fogos não têm registro naqueles anos (ponto 1 da revisão do PR #1). O calendário continua usando o fator por contagens.
- **Entrega duas coisas para a tela de Método:**
  1. **A curva de detecção:** "um fogo de 2 MW tem X% de chance de ser visto pelo MODIS; um de 50 MW, Y%", separada para dia e noite. Explica sem jargão por que o fator noturno é cerca de 5 vezes o diurno e por que juntar as séries sem tratamento infla ou esconde fogo.
  2. **A prova cruzada do fator:** a soma das chances previstas para os fogos do VIIRS estima quantos fogos o MODIS deveria ver. A razão "fogos do VIIRS ÷ soma das chances" é um fator calculado por outro caminho. Se ele ficar perto do fator por contagens, são **dois métodos independentes concordando**.

## Decisão: caminho C

| Etapa | Dados | Quem roda | Quando | Corte de treino e teste |
| --- | --- | --- | --- | --- |
| **A** | Arquivos de 2024 do Brasil inteiro que já estão no repositório (`data-pipeline/data/`, S-NPP e Aqua) | Frente B, sem depender do banco | Sábado à noite | **No espaço:** blocos da grade H3 sorteados para treino e teste, com todos os meses dos dois lados |
| **B** | Histórico do banco de teste | Frente A, com o mesmo script | Domingo de manhã, **só se couber** sem atrasar o servidor público | **No tempo:** treino em 2019 a 2021, teste em 2022 a 2024 (anos que o modelo não vê; mostra se a deriva do Aqua atrapalha) |

A etapa A sozinha já entrega a curva e a prova cruzada. A etapa B reforça com anos que o modelo nunca viu.

## Proposta (etapa A)

1. **Formar os pares**, com a regra já escrita em [regras-variaveis.md](../regras-variaveis.md), seção 4:
   - mesma data e mesmo período (dia ou noite), com até 10 minutos de diferença **quando o Aqua estava na órbita original (até 2021)**. Em 2024 a janela precisa ser de 90 minutos (ver "O que a etapa A mostrou");
   - **"o MODIS viu"**: a distância entre os dois focos é no máximo metade do maior entre `scan` e `track` do MODIS, mais metade do pixel do VIIRS (0,19 km);
   - **"o MODIS estava olhando"**: há algum foco do Aqua a até 50 km, na mesma passagem. Os fogos sem isso ficam fora do treino. ESCOLHA DA EQUIPE, com viés declarado (abaixo).
   - Só os filtros que já valem no projeto: `type = 0`, FRP maior que zero, confiança nominal e alta, biomas do IBGE.
2. **Corte no espaço:** sortear blocos H3 de resolução 4 (cerca de 1.770 km² cada) para treino (metade) e teste (metade), com semente fixa. Blocos grandes evitam que fogos vizinhos, que se parecem, caiam um no treino e outro no teste. ESCOLHA DA EQUIPE.
3. **Dois modelos, lado a lado:**
   - **tabela simples:** chance de detecção por faixa de FRP (abaixo de 2, 2 a 5, 5 a 10, 10 a 25 e 25 MW ou mais), dia ou noite e bioma. Fácil de explicar e não precisa de biblioteca nova;
   - **gradient boosting** (`HistGradientBoostingClassifier`, do scikit-learn), o modelo do plano original, com todas as pistas.
4. **Medidas nos blocos de teste:**
   - **separação:** quão bem o modelo distingue fogos vistos e não vistos (AUC: 1 é perfeito, 0,5 é sorteio);
   - **calibração:** se as chances previstas batem com o que aconteceu, por faixa (quando o modelo diz 30%, o MODIS viu cerca de 30% daqueles fogos?);
   - **prova cruzada:** o fator implícito por bioma, mês e dia ou noite, comparado com o fator por contagens de 2024.
5. **Testes antes do código** ([testes.md](../testes.md), regra 1), com dados inventados de chance conhecida, como os da calibração.

**Saídas:** um relatório e CSVs pequenos (curva de detecção, medidas, comparação dos fatores) e um gráfico da curva com rótulos em inglês. **Nada é gravado no banco.**

## Sequência de etapas

A ordem de execução do caminho C. Cada passo só começa depois do anterior, e o **ponto de corte** está marcado.

### Preparação

| Passo | O quê | Quem |
| --- | --- | --- |
| 0.1 | Revisão deste PR: o Mateus e o Eduardo respondem às duas perguntas (tamanho dos blocos do teste e se a etapa B cabe no domingo) | Mateus e Eduardo |
| 0.2 | Decisões finais: as faixas de potência da tabela simples (abaixo de 2, 2 a 5, 5 a 10, 10 a 25 e 25 MW ou mais) e o uso da biblioteca scikit-learn | Weberson |

### Etapa A: modelo com os dados de 2024 (frente B, cerca de 3 a 4 horas)

| Passo | O quê | Tempo |
| --- | --- | --- |
| 1 | Abrir uma branch só para o código do modelo, separada do PR #26 | minutos |
| 2 | **Testes primeiro**, com dados inventados de resposta conhecida: o pareamento acha o fogo certo por distância e horário; a regra dos 50 km funciona; o sorteio dos blocos não põe vizinhos dos dois lados; o modelo recupera uma chance de detecção plantada; a prova cruzada recupera um fator conhecido. Rodar e ver falhar | 45 min |
| 3 | Formar os pares de 2024, **reaproveitando as regras de limpeza do `pipeline.py` (frente A), sem copiá-las** | 1 h |
| 4 | Separar treino e teste no espaço: sortear blocos H3, com semente fixa, metade para cada lado | 15 min |
| 5 | Modelo 1, a tabela simples: chance de detecção por faixa de potência, dia ou noite e bioma | 20 min |
| 6 | Modelo 2, o gradient boosting, com todas as pistas | 30 min |
| 7 | Medir nos blocos de teste: separação, calibração e **prova cruzada** com o fator por contagens | 30 min |
| 8 | Gerar a curva de detecção em gráfico, com rótulos em inglês | 15 min |
| 9 | Abrir o PR do código: checagens de código morto e de cobertura, linha de uso de IA no README, sem `Co-Authored-By`, Mateus revisando | 20 min |

**Ponto de corte:** se o gradient boosting (passo 6) não ficar pronto até a meia-noite, seguimos só com a tabela simples, que já entrega a curva e a prova cruzada.

### Etapa B: modelo com o histórico (frente A, domingo de manhã, opcional)

| Passo | O quê | Quem |
| --- | --- | --- |
| 10 | Acrescentar ao script um modo que lê o banco, como o `calibrar.py` já faz | Frente B |
| 11 | Rodar no banco de teste, **sem gravar nada**: treino em 2019 a 2021, teste em 2022 a 2024, e mandar os CSVs | Eduardo |
| 12 | Comparar com a etapa A e ver se a deriva do Aqua atrapalha nos anos recentes | Frente B |

Só entra se a frente A tiver tempo **depois** de levar o banco para o servidor público. Se não couber, fica declarado como próximo passo.

### Registro e entrega

| Passo | O quê |
| --- | --- |
| 13 | Registrar os resultados no `decisoes-harmonizacao.md` (seção 5) e criar a tarefa B7 no `tarefas.md`, depois que o PR #26 entrar |
| 14 | Entregar à frente D a curva de detecção e a frase da prova cruzada, em inglês, para a tela de Método |
| 15 | Declarar os limites da seção "Limites a declarar no Método" |

## Prazos e ponto de corte

- **Etapa A até a meia-noite de sábado.** Se o gradient boosting não ficar pronto, fica só a tabela simples, que já entrega a curva e a prova cruzada.
- **Etapa B no domingo de manhã, só se a frente A tiver tempo** depois de levar o banco para o servidor. Se não couber, fica como próximo passo, declarado.
- **O modelo não pode atrasar o essencial:** os fatores no servidor público, a API, o front e a tela de Método.

## Dependência nova

O gradient boosting precisa do **scikit-learn** no `requirements.txt` do `data-pipeline`. Ele entra no PR do código, para a revisão avaliar. A tabela simples não precisa dele.

## Limites a declarar no Método

- **Viés da regra dos 50 km:** ela descarta justamente as áreas onde o VIIRS viu fogo e o MODIS não viu nada perto, então a chance de detecção sai mais alta do que é.
- **O pixel do MODIS onde ele não detectou** é aproximado pelo tamanho mediano dos pixels daquela passagem.
- **Etapa A com um ano só (2024)** e corte no espaço: não mede a deriva do Aqua. Isso fica para a etapa B.
- **O modelo não converte a série histórica.** A conversão do calendário é o fator por contagens.

## Impacto nas frentes

| Frente | O que muda |
| --- | --- |
| **A (dados)** | Só a etapa B, opcional: rodar o script no banco de teste (sem gravar nada) e mandar os CSVs. Estimativa: cerca de 1 hora, com a execução |
| **C (API)** | Nenhum campo novo. O modelo não entra no cálculo do calendário |
| **D (front)** | A tela de Método ganha a curva de detecção (imagem ou dados) e uma frase sobre a prova cruzada. Os textos saem do relatório |

## O que a etapa A mostrou (14/11/2026, dados de 2024)

O código está no PR #53 e o resultado completo no `decisoes-harmonizacao.md`, seção 5. Em resumo:

1. **A janela de 10 minutos não serve para 2024.** O Aqua passa 44 minutos (dia) e 63 minutos (noite) depois do S-NPP no mesmo lugar (deriva de órbita desde 2022), e só 6% a 9% dos pares ficam dentro de 10 minutos. A janela virou parâmetro, e o resultado usa 90 minutos. Com isso, "viu" mistura a sensibilidade do sensor com a mudança do fogo ao longo da hora que separa as passagens. **A etapa B (2019 a 2021 para treino, com o Aqua ainda na órbita original) passa a ser o experimento mais limpo**, e não só um reforço.
2. **A curva de detecção funciona.** A chance de o MODIS ver um fogo do VIIRS sobe com a potência: de dia, de 15% (abaixo de 2 MW) a 71% (25 MW ou mais); de noite, de 18% a 87%. O gradient boosting separa melhor que a tabela (AUC 0,753 contra 0,708, com referência em 0,5).
3. **A prova cruzada, como foi definida, compara unidades diferentes e não é um teste do fator por contagens.** De dia a razão fica perto de 1 em Amazônia, Mata Atlântica e Cerrado (0,76 a 1,05); de noite fica entre 0,29 e 0,44 em todos os biomas. Verificado nos dados: com a calibração boa, o fator do modelo conta fogos do VIIRS cobertos por um pixel do MODIS, e o fator por contagens conta fogos do Aqua; cada foco do Aqua cobre em média 1,2 fogo do VIIRS de dia e 3,2 de noite, o que basta para explicar a razão sem defeito em nenhum dos dois fatores. O viés da regra dos 50 km é uma segunda causa provável, não testada. **A promessa "dois métodos independentes concordando" não se sustenta com esta definição**, nem foi desmentida. O que o modelo entrega com segurança é a curva, para áreas que o MODIS estava olhando.

## Relação com outros documentos

- [decisoes-harmonizacao.md](../decisoes-harmonizacao.md), seção 5, já descreve o classificador como complementar, com treino em 2019 a 2021 e teste em 2022 a 2024. Este RFC detalha como ele é feito e muda o status para **entrega**. A seção 5 e o `tarefas.md` (uma tarefa B7) serão atualizados depois que o PR #26 entrar, para não conflitar com ele.
- Regras dos pares: [regras-variaveis.md](../regras-variaveis.md), seção 4.
