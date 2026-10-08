# Turismo no Brasil (2015–2024)

Projeto G1 · Linguagem de Programação — Análise e Visualização de Dados com Python · **Tema 18**

**Aluna:** Marcella Guimarães Rodrigues da Silva  
**Professor:** Alexandre Neves Louzada
**Matéria:** Linguagens de Programação

## Links

- **Dashboard (Streamlit):** https://turismo-brasil-marcella.streamlit.app/
- **Página do projeto (GitHub Pages):** https://marcellaguimaraesrodrigues.github.io/projeto-turismo-brasil/
- **Notebook:** [notebooks/analise_turismo.ipynb](notebooks/analise_turismo.ipynb)

## Sobre o projeto

Análise de uma base simulada do turismo brasileiro entre 2015 e 2024 (4.440 registros, 37 cidades, 20 estados).
O projeto busca responder quais cidades recebem mais turistas, se existe alta temporada, quais regiões movimentam
mais recursos, como o turismo evoluiu ao longo do tempo e se o clima influencia o fluxo de visitantes.

## Principais resultados

- O número de turistas ficou estável, com o ponto mais baixo em 2020 e recuperação a partir de 2023.
- Aparecida de Goiânia é a cidade mais visitada; a diferença entre as 10 primeiras é pequena.
- O Sudeste tem o maior faturamento por concentrar mais cidades; por cidade, as regiões ficam parecidas.
- Não há alta temporada forte (pico em junho, vale em abril, amplitude de ~10 p.p.).
- O clima não influencia o turismo (correlação de −0,01 entre temperatura e turistas).

## Dashboard

O dashboard em Streamlit tem filtros por ano, mês, região, estado, cidade e nível de temporada, e está dividido em páginas:

- **Visão geral:** KPIs (total de turistas, faturamento, ocupação hoteleira, gasto médio, cidade mais visitada, região mais movimentada) e evolução mensal
- **Evolução e sazonalidade:** turistas por ano, variação anual, índice sazonal e heatmap mensal
- **Destinos turísticos:** ranking de cidades, crescimento e dispersão turistas × faturamento
- **Regiões e mapa:** comparação regional e mapa interativo por estado
- **Clima e correlação:** temperatura × turistas e matriz de correlação
- **Tabela dinâmica:** cruzamento livre das dimensões da base
- **Consultas SQL:** consultas ao banco SQLite criado com SQLAlchemy
- **Conclusão executiva:** respostas às perguntas orientadoras e limitações

## Tratamento dos dados

- Sem valores nulos nem duplicados.
- 260 registros tinham mais turistas estrangeiros que o total; os estrangeiros foram limitados ao total.
- Novas colunas: percentual de estrangeiros, faturamento por turista e período mensal.

## Estrutura

```
projeto-turismo-brasil/
├── app.py              # dashboard Streamlit (multipágina)
├── requirements.txt
├── README.md
├── index.html          # página do projeto (GitHub Pages)
├── dados/              # base CSV
├── database/           # banco SQLite (SQLAlchemy)
├── notebooks/          # notebook de análise
└── imagens/            # gráficos usados na página
```

## Tecnologias

Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, SQLAlchemy, SQLite e GitHub.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

> Os dados são simulados e servem para praticar técnicas de análise.
