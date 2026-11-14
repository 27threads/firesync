# Requisitos — Calendário Harmonizado de Focos de Calor (MODIS + VIIRS)

Nov 13, 2026 · @Mateus Nogueira

Este documento separa o que o desafio **exige** (está nos Objetivos) do que ele só **sugere** (aparece como "pode considerar"). Assim fica claro o mínimo para entregar e o que dá pontos extras.

## 1. Requisitos obrigatórios

### Parte A: Harmonização dos dados (backend / pipeline)

- **RF01:** Buscar os focos de calor do **MODIS** (Terra e Aqua). É a série histórica, do início dos anos 2000 em diante.
- **RF02:** Buscar os focos de calor do **VIIRS**. É o sensor que continua a série, com mais detalhe.
- **RF03:** Harmonizar as duas fontes numa **série temporal única e consistente**. Depois dessa etapa, "o sensor de origem não importa mais". O processo precisa compensar as diferenças entre os dois sensores:
  - resolução espacial (VIIRS \~375 m, MODIS \~1 km)
  - sensibilidade de detecção (o VIIRS detecta mais focos pequenos)
  - horário em que cada satélite passa
- **RF04:** Cobrir o período **do início dos anos 2000 até hoje**, com dados atualizados.
- **RF05:** Entregar os dados harmonizados como **entrada da aplicação web**.

### Parte B: Aplicação web (frontend + API)

- **RF06:** Deixar o usuário **escolher uma região / área de interesse**.
- **RF07:** Deixar o usuário **escolher um intervalo de datas**.
- **RF08:** Mostrar um **calendário de atividade de queimadas** com o **número de focos de calor** da área escolhida, no formato meses × anos.
- **RF09:** Mostrar **quais meses do ano têm mais fogo** (o padrão sazonal).
- **RF10:** Mostrar **quais anos tiveram mais fogo**.
- **RF11:** Comparar o **mês atual com a mediana histórica** da área.
- **RF12:** Mostrar **como a atividade atual se compara a períodos anteriores**, ou seja, as anomalias.
- **RF13:** Permitir **baixar as análises e visualizações** da busca.

## 2. Requisitos desejáveis (diferenciais)

- **RD01:** **Mapa interativo** em que o usuário desenha a área de interesse (polígono ou retângulo).
- **RD02:** Opção de **digitar latitude e longitude**, como alternativa ao desenho no mapa.
- **RD03:** **Rampa de cores** no calendário, para mostrar as diferenças entre meses como um heatmap.
- **RD04:** Cores **acessíveis**, legíveis para quem tem daltonismo (por exemplo, viridis ou cividis).
- **RD05:** **Exportar um CSV** com os focos de calor encontrados na busca.
- **RD06:** **Indicadores principais** em destaque:
  - número total de focos detectados e registrados
  - anomalia em relação à média de vários anos
- **RD07:** Interface pensada para o **público-alvo**: equipes de alerta precoce, resposta a emergências, cientistas, gestores de terras e bombeiros. Precisa ser rápida de ler e de usar.

## 3. Requisitos não funcionais (implícitos no texto)

- **RNF01:** Ser uma **aplicação web**, acessada pelo navegador.
- **RNF02:** **Fonte de dados:** o texto sugere o **NASA FIRMS** (Earthdata), que fornece os dados do MODIS e do VIIRS.
- **RNF03:** **Atualização contínua.** O calendário precisa estar "atualizado", então os dados novos devem entrar periodicamente.
- **RNF04:** **Desempenho.** São mais de 20 anos de focos no mundo inteiro, então as consultas por área e período precisam ser rápidas. Isso pede pré-agregação e indexação espacial.
- **RNF05:** **Usabilidade e acessibilidade**, porque o usuário pode estar numa situação de emergência.

### Definidos pela equipe

Não vêm do texto do desafio. São necessários porque o sistema é público e precisa estar sempre atualizado para o público de emergência (RD07).

- **RNF06:** **Limite de requisições na API.** A API é pública, e uma área grande (até 250 mil células) custa caro. Sem limite, uma pessoa ou um robô consegue derrubar o servidor.
  - Limite por IP, com valores em configuração. Proposta inicial: 60 pedidos por minuto no geral, 10 por minuto em `POST /calendar` e 2 por minuto em `POST /export`.
  - Acima do limite: HTTP `429` com o código `rate_limited` e o cabeçalho `Retry-After`.
  - Um segundo limite no servidor web (ver `infra/`), antes de o pedido chegar à API.
- **RNF07:** **Monitoramento.**
  - **Dado velho:** se o `updated_at` passar de **6 horas** (duas rodadas do job NRT perdidas), a equipe recebe um aviso, e a tela mostra ao usuário que os dados podem estar desatualizados. Para o público de emergência, mostrar dado velho como se fosse atual é pior do que avisar.
  - **Logs da API:** cada pedido registra o endpoint, o tempo de resposta, o número de células da área e o status HTTP.
  - **Logs do job NRT:** cada rodada registra quantos focos entraram, quanto tempo levou e os erros.
  - O canal do aviso (e-mail, Discord, Telegram) é decidido no deploy.
- **RNF08:** **Testes automáticos (CI).** Todo PR com código roda os testes sozinho, pelo GitHub Actions, e só entra na `main` se passar. Detalhes em [arquitetura.md](arquitetura.md), seção "Qualidade e testes".

## 4. Decisões que o texto deixa em aberto

O enunciado não diz como fazer estes pontos, e eles vão definir a arquitetura:

1. **Método de harmonização.** Por exemplo: agregar os focos numa grade comum (como 0,25° ou 1 km) e calcular um fator de calibração no período em que os dois sensores funcionaram juntos (2012 em diante). Outra opção é filtrar por confiança ou potência radiativa (FRP).
2. **Granularidade do calendário:** contagem mensal ou diária.
3. **Escopo geográfico:** o mundo todo ou só o Brasil num primeiro momento (muda muito o volume de dados).
4. **Dados pré-processados ou consulta à API do FIRMS na hora.** A API do FIRMS tem limites, então pré-processar é mais seguro.
5. **Formato do download** pedido no RF13: PNG, PDF ou CSV.

## 5. Entregáveis da submissão (Space Apps 2026)

A submissão fecha no domingo, 15/11, às 23h59 no horário do evento local. Dá para reenviar até lá, e vale a última versão. [Guia de submissão](https://www.spaceappschallenge.org/resources/project-submission-guide/) · [Página do desafio](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/)

### Página do projeto (tudo em inglês)

- [ ] Project Name
- [ ] High-Level Project Summary: o que foi feito, como resolve o desafio, por que importa
- [ ] Link to Project Demo (público, sem login)
- [ ] Link to Final Project: app no ar e/ou repositório (público, sem login)
- [ ] Detailed Project Description: o que faz, como funciona, benefícios, ferramentas e linguagens
- [ ] NASA Data: FIRMS (MODIS e VIIRS) e o que mais usarmos (GIBS, POWER). Mínimo de um recurso da NASA para concorrer ao prêmio global
- [ ] Space Agency Partner Data and Other References: todas as fontes, bibliotecas e imagens. Considerar dados de parceiras (INPE/AEB, CONAE)
- [ ] Use of Super Intelligence: declarar onde e como IA foi usada
- [ ] Marcar "Terms and Conditions" e "Confirm All Work is Original" e clicar em "Submit for Judging"

### Demo

- [ ] Escolher o formato: vídeo de até 30 s ou até 7 slides (contando título e introdução). Passar do limite tira o projeto do julgamento global
- [ ] Vídeo com legenda em inglês (a fala pode ser em português) ou slides em inglês
- [ ] Conteúdo obrigatório: nome da equipe, nomes dos membros, desafio escolhido, imagem do projeto, experiência do usuário e como os dados abertos da NASA tornaram o projeto possível
- [ ] Hospedar fora do site (YouTube, Drive, GitHub) e testar o link numa janela anônima
- [ ] Sem imagem, vídeo ou voz de menores de 18 anos
- [ ] Definir um responsável pela demo e pela página

### Aplicação

- [ ] Interface em inglês
- [ ] Crédito ao FIRMS visível no app
- [ ] Identificar código gerado com IA em texto descritivo ou metadados (ex.: README)
- [ ] Pedir a classificação FortiGuard do site para os jurados não terem o acesso bloqueado (recomendado, não obrigatório)

### Elegibilidade

- [ ] Todos os membros confirmados no mesmo evento local

Os critérios de julgamento são Impact, Creativity, Validity, Relevance e Presentation. O guia diz que a IA não deve ser usada para criar a ideia de como resolver o desafio, então a abordagem final precisa ser da equipe.
