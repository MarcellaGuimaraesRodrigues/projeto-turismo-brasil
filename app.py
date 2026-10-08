import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Turismo no Brasil", page_icon="✈️", layout="wide")

# ---------- Carregamento e tratamento dos dados ----------
@st.cache_data
def carregar_dados():
    df = pd.read_csv("dados/simulacao_turismo_brasil.csv")
    df["data"] = pd.to_datetime(df["data"])
    # Corrige registros com mais estrangeiros que o total de turistas
    df["turistas_estrangeiros"] = df[["turistas_estrangeiros", "turistas"]].min(axis=1)
    df["perc_estrangeiros"] = (df["turistas_estrangeiros"] / df["turistas"] * 100).round(2)
    df["faturamento_por_turista"] = (df["faturamento_turismo"] / df["turistas"]).round(2)
    return df


@st.cache_resource
def salvar_no_banco(df):
    # Persistência em banco SQLite usando SQLAlchemy
    os.makedirs("database", exist_ok=True)
    engine = create_engine("sqlite:///database/turismo.db")
    df.to_sql("turismo", engine, if_exists="replace", index=False)
    return engine


df = carregar_dados()
engine = salvar_no_banco(df)

# ---------- Cabeçalho ----------
st.title("✈️ Turismo no Brasil (2015–2024)")
st.markdown(
    "Este dashboard analisa dados simulados do turismo brasileiro para identificar os destinos "
    "mais visitados, a evolução do turismo ao longo do tempo, as diferenças entre regiões e os "
    "fatores que influenciam o fluxo de turistas."
)

# ---------- Filtros ----------
st.sidebar.header("Filtros")
anos = st.sidebar.multiselect("Ano", sorted(df["ano"].unique()), default=sorted(df["ano"].unique()))
meses = st.sidebar.multiselect("Mês", list(range(1, 13)), default=list(range(1, 13)))
regioes = st.sidebar.multiselect("Região", sorted(df["regiao"].unique()), default=sorted(df["regiao"].unique()))

ufs_disp = sorted(df[df["regiao"].isin(regioes)]["uf"].unique())
ufs = st.sidebar.multiselect("Estado", ufs_disp, default=ufs_disp)

cidades_disp = sorted(df[df["uf"].isin(ufs)]["cidade"].unique())
cidades = st.sidebar.multiselect("Cidade", cidades_disp, default=cidades_disp)

temporadas = st.sidebar.multiselect(
    "Nível de temporada", ["Alta", "Média", "Baixa"], default=["Alta", "Média", "Baixa"]
)

filtro = (
    df["ano"].isin(anos)
    & df["mes"].isin(meses)
    & df["regiao"].isin(regioes)
    & df["uf"].isin(ufs)
    & df["cidade"].isin(cidades)
    & df["nivel_temporada"].isin(temporadas)
)
dff = df[filtro]

if dff.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# ---------- KPIs dinâmicos ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de turistas", f"{dff['turistas'].sum() / 1e6:,.1f} mi")
c2.metric("Faturamento total", f"R$ {dff['faturamento_turismo'].sum() / 1e9:,.1f} bi")
c3.metric("Ocupação hoteleira média", f"{dff['ocupacao_hoteleira'].mean():.1f}%")
c4.metric("Gasto médio por turista", f"R$ {dff['gasto_medio'].mean():,.2f}")

c5, c6 = st.columns(2)
c5.metric("Cidade mais visitada", dff.groupby("cidade")["turistas"].sum().idxmax())
c6.metric("Região com maior faturamento", dff.groupby("regiao")["faturamento_turismo"].sum().idxmax())

# ---------- Seções ----------
aba1, aba2, aba3, aba4, aba5 = st.tabs(
    ["📈 Evolução", "🏙️ Destinos", "🗺️ Regiões", "🌡️ Clima e correlação", "🗄️ Dados"]
)

with aba1:
    st.subheader("Evolução do turismo ao longo do tempo")
    por_ano = dff.groupby("ano")["turistas"].sum().reset_index()
    fig = px.line(por_ano, x="ano", y="turistas", markers=True,
                  labels={"ano": "Ano", "turistas": "Total de turistas"})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Sazonalidade (média de turistas por mês)")
    por_mes = dff.groupby("mes")["turistas"].mean().reset_index()
    fig = px.bar(por_mes, x="mes", y="turistas",
                 labels={"mes": "Mês", "turistas": "Média de turistas"})
    st.plotly_chart(fig, width="stretch")

    st.info(
        "O número de turistas se manteve relativamente estável, com o ponto mais baixo em 2020 "
        "(pandemia) e recuperação a partir de 2023. Não há alta temporada muito marcada: junho tem "
        "a maior média e abril a menor, com diferença de cerca de 10%."
    )

with aba2:
    st.subheader("Top 10 destinos mais visitados")
    top = dff.groupby("cidade")["turistas"].sum().nlargest(10).sort_values().reset_index()
    fig = px.bar(top, x="turistas", y="cidade", orientation="h",
                 labels={"turistas": "Total de turistas", "cidade": ""})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Destinos com maior crescimento (primeiro x último ano selecionado)")
    if len(anos) >= 2:
        a0, a1 = min(anos), max(anos)
        cresc = dff[dff["ano"].isin([a0, a1])].pivot_table(
            index="cidade", columns="ano", values="turistas", aggfunc="sum"
        ).dropna()
        cresc.columns = [str(c) for c in cresc.columns]
        cresc["crescimento_%"] = ((cresc[str(a1)] / cresc[str(a0)] - 1) * 100).round(1)
        st.dataframe(cresc.sort_values("crescimento_%", ascending=False).head(10))
    else:
        st.write("Selecione pelo menos dois anos para ver o crescimento.")

    st.info(
        "Aparecida de Goiânia lidera o ranking, à frente de destinos tradicionais. A diferença entre "
        "as dez primeiras cidades é pequena, o que indica um fluxo bem distribuído entre os destinos."
    )

with aba3:
    st.subheader("Faturamento por região")
    reg = dff.groupby("regiao").agg(
        faturamento=("faturamento_turismo", "sum"), cidades=("cidade", "nunique")
    ).reset_index()
    reg["faturamento_bi"] = reg["faturamento"] / 1e9
    reg["faturamento_por_cidade_bi"] = reg["faturamento_bi"] / reg["cidades"]
    col_a, col_b = st.columns(2)
    fig = px.bar(reg.sort_values("faturamento_bi", ascending=False), x="regiao", y="faturamento_bi",
                 labels={"regiao": "Região", "faturamento_bi": "Faturamento (R$ bi)"},
                 title="Faturamento total")
    col_a.plotly_chart(fig, width="stretch")
    fig = px.bar(reg.sort_values("faturamento_por_cidade_bi", ascending=False), x="regiao",
                 y="faturamento_por_cidade_bi",
                 labels={"regiao": "Região", "faturamento_por_cidade_bi": "R$ bi por cidade"},
                 title="Faturamento por cidade")
    col_b.plotly_chart(fig, width="stretch")

    st.subheader("Ocupação hoteleira média por região")
    ocup = dff.groupby("regiao")["ocupacao_hoteleira"].mean().reset_index()
    fig = px.bar(ocup, x="regiao", y="ocupacao_hoteleira",
                 labels={"regiao": "Região", "ocupacao_hoteleira": "Ocupação média (%)"})
    st.plotly_chart(fig, width="stretch")

    st.info(
        "O Sudeste tem o maior faturamento total porque concentra mais cidades turísticas na base. "
        "Quando dividido pelo número de cidades, o faturamento das regiões fica muito parecido."
    )

with aba4:
    st.subheader("Clima x turismo")
    fig = px.scatter(dff, x="temperatura_media", y="turistas", color="regiao", opacity=0.5,
                     labels={"temperatura_media": "Temperatura média (°C)", "turistas": "Turistas"})
    st.plotly_chart(fig, width="stretch")

    st.subheader("Matriz de correlação")
    cols = ["turistas", "temperatura_media", "ocupacao_hoteleira", "eventos_realizados", "gasto_medio"]
    corr = dff[cols].corr().round(2)
    fig = px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
    st.plotly_chart(fig, width="stretch")

    st.info(
        "A correlação entre temperatura e número de turistas é praticamente zero, ou seja, o clima "
        "não influencia o fluxo turístico nesta base."
    )

with aba5:
    st.subheader("Consulta ao banco de dados SQLite")
    consulta = pd.read_sql(
        "SELECT regiao, COUNT(DISTINCT cidade) AS cidades, SUM(turistas) AS turistas, "
        "ROUND(AVG(ocupacao_hoteleira), 1) AS ocupacao_media "
        "FROM turismo GROUP BY regiao ORDER BY turistas DESC",
        engine,
    )
    st.dataframe(consulta, width="stretch")

    st.subheader("Dados filtrados")
    st.dataframe(dff, width="stretch")

# ---------- Conclusão ----------
st.header("Conclusão executiva")
st.markdown(
    "- O **Sudeste** é a região que mais fatura com turismo, principalmente por concentrar mais cidades.\n"
    "- O **clima não influencia** o fluxo de turistas (correlação próxima de zero).\n"
    "- O ranking de destinos surpreende: **Aparecida de Goiânia** aparece em primeiro lugar.\n"
    "- O turismo se manteve estável, com queda em 2020 e recuperação a partir de 2023.\n\n"
    "_Os dados são simulados e servem para praticar técnicas de análise._"
)
