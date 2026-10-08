"""
Dashboard — Turismo no Brasil (2015–2024)
Projeto G1 · Linguagem de Programação — Análise e Visualização de Dados com Python

Tecnologias: Python, Pandas, NumPy, Matplotlib, Seaborn, Plotly, Streamlit, SQLAlchemy + SQLite.
Executar com:  streamlit run app.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
import streamlit as st
from matplotlib.ticker import FuncFormatter
from sqlalchemy import create_engine, inspect

st.set_page_config(page_title="Turismo no Brasil · Dashboard", layout="wide")

BASE = Path(__file__).parent
CSV_PATH = BASE / "dados" / "simulacao_turismo_brasil.csv"
DB_PATH = BASE / "database" / "turismo.db"

PRIMARY = "#1F4E79"
ACCENT = "#E07A1F"
GREY = "#B8C2CC"
REG_PAL = {
    "Norte": "#4C9F70",
    "Nordeste": "#E07A1F",
    "Centro-Oeste": "#8E6BBF",
    "Sudeste": "#1F4E79",
    "Sul": "#C2185B",
}
MESES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
         7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
TEMPORADAS = ["Alta", "Média", "Baixa"]

UF_COORD = {
    "AM": (-3.4, -65.0), "BA": (-12.9, -41.7), "CE": (-5.2, -39.3), "DF": (-15.8, -47.9),
    "ES": (-19.6, -40.5), "GO": (-15.9, -49.8), "MA": (-5.0, -45.3), "MG": (-18.5, -44.6),
    "MS": (-20.5, -54.5), "MT": (-12.9, -55.9), "PA": (-3.8, -52.5), "PB": (-7.1, -36.8),
    "PE": (-8.4, -37.9), "PR": (-24.6, -51.6), "RJ": (-22.2, -42.7), "RO": (-10.9, -62.8),
    "RS": (-29.7, -53.5), "SC": (-27.2, -50.5), "SP": (-22.2, -48.8), "TO": (-10.2, -48.3),
}

sns.set_theme(style="whitegrid", context="notebook", font_scale=0.95,
              rc={"axes.spines.top": False, "axes.spines.right": False})


# ---------------------------------------------------------------- formatação
def _br(s: str) -> str:
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def brl(v: float) -> str:
    return _br(f"R$ {v:,.2f}")


def bi(v: float) -> str:
    return _br(f"R$ {v / 1e9:,.1f} bi")


def mil(v: float) -> str:
    return _br(f"{v / 1e6:,.1f} mi")


def num(v: float, casas: int = 0) -> str:
    return _br(f"{v:,.{casas}f}")


def pct(v: float, casas: int = 1) -> str:
    return _br(f"{v:,.{casas}f}%")


# ---------------------------------------------------------------- dados
def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Limpeza e engenharia de atributos (mesma lógica do notebook)."""
    df = df.copy()
    df.columns = [c.replace("﻿", "").strip().lower() for c in df.columns]
    df["data"] = pd.to_datetime(df["data"])
    df = df.dropna().drop_duplicates()

    # registros inconsistentes: estrangeiros > total de turistas
    df["inconsistente"] = df["turistas_estrangeiros"] > df["turistas"]
    df["turistas_estrangeiros"] = df[["turistas_estrangeiros", "turistas"]].min(axis=1)

    # engenharia de atributos
    df["perc_estrangeiros"] = df["turistas_estrangeiros"] / df["turistas"] * 100
    df["faturamento_por_turista"] = df["faturamento_turismo"] / df["turistas"]
    df["periodo"] = df["data"].dt.to_period("M").dt.to_timestamp()
    return df.reset_index(drop=True)


@st.cache_resource
def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH.as_posix()}")


@st.cache_data(show_spinner="Carregando base de dados…")
def carregar_base() -> pd.DataFrame:
    """Lê a tabela `turismo` do SQLite; se o banco não existir, cria a partir do CSV."""
    engine = get_engine()
    if "turismo" not in inspect(engine).get_table_names():
        bruto = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        preparar(bruto).to_sql("turismo", engine, if_exists="replace", index=False)
    return pd.read_sql("SELECT * FROM turismo", engine, parse_dates=["data", "periodo"])


def resumo(df: pd.DataFrame, por: str) -> pd.DataFrame:
    g = df.groupby(por).agg(
        turistas=("turistas", "sum"),
        estrangeiros=("turistas_estrangeiros", "sum"),
        faturamento=("faturamento_turismo", "sum"),
        ocupacao=("ocupacao_hoteleira", "mean"),
        gasto_medio=("gasto_medio", "mean"),
        cidades=("cidade", "nunique"),
    )
    g["perc_estrangeiros"] = g["estrangeiros"] / g["turistas"] * 100
    g["faturamento_por_cidade"] = g["faturamento"] / g["cidades"]
    return g


def indice_sazonal(df: pd.DataFrame) -> pd.Series:
    """Média de turistas de cada mês dividida pela média mensal geral (1,00 = média)."""
    mensal = df.groupby(["ano", "mes"])["turistas"].sum()
    return mensal.groupby("mes").mean() / mensal.mean()


# ---------------------------------------------------------------- gráficos
def mostrar(fig) -> None:
    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)
    plt.close(fig)


def barras(ax, serie: pd.Series, fmt, horizontal: bool = True, destaque: bool = True,
           ordenar: bool = True) -> None:
    """Barras ordenadas (maior → menor) com rótulos e destaque no líder."""
    s = serie.sort_values(ascending=False) if ordenar else serie
    chaves = s.index.astype(str)
    cores = {k: (ACCENT if (i == 0 and destaque) else PRIMARY) for i, k in enumerate(chaves)}
    if horizontal:
        sns.barplot(x=s.values, y=chaves, hue=chaves, palette=cores, legend=False, ax=ax)
        for i, v in enumerate(s.values):
            ax.text(v, i, " " + fmt(v), va="center", fontsize=9)
        ax.set_xlim(0, s.max() * 1.25)
        ax.set_xticks([])  # os valores já aparecem ao lado das barras
    else:
        sns.barplot(x=chaves, y=s.values, hue=chaves, palette=cores, legend=False, ax=ax)
        for i, v in enumerate(s.values):
            ax.text(i, v, fmt(v), ha="center", va="bottom", fontsize=9)
        ax.set_ylim(0, s.max() * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    ax.set_xlabel("")
    ax.set_ylabel("")


def plotly_layout(fig) -> None:
    fig.update_layout(template="plotly_white", hovermode="x unified",
                      margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    fig.update_yaxes(separatethousands=True)


def mostrar_plotly(fig) -> None:
    st.plotly_chart(fig, width="stretch")


def interpretacao(*linhas: str) -> None:
    st.info(("**Interpretação.** " + " ".join(linhas)).replace("R$", "R\\$"))


def md(texto: str) -> None:
    """Markdown com o cifrão escapado (o Streamlit interpreta $ como fórmula)."""
    st.markdown(texto.replace("R$", "R\\$"))


def cabecalho(titulo: str, subtitulo: str) -> None:
    st.title(titulo)
    st.caption(subtitulo)


CTX: dict = {}


# ---------------------------------------------------------------- páginas
def pagina_visao_geral() -> None:
    df, total = CTX["df"], CTX["df_all"]
    cabecalho("Turismo no Brasil (2015–2024)", "Visão geral · KPIs e evolução do turismo")

    st.markdown(
        """
**O problema.** O turismo é uma atividade econômica importante, que gera empregos, movimenta
recursos e impulsiona o desenvolvimento regional. Este dashboard investiga uma base **simulada**
do turismo brasileiro (2015–2024) para responder: *quais cidades recebem mais turistas? Existe alta
temporada? Quais regiões movimentam mais recursos? Como o turismo evoluiu ao longo do tempo?
O clima influencia o fluxo de visitantes?*

Use os **filtros na barra lateral** — todos os KPIs, gráficos e interpretações se recalculam.
        """
    )

    cid = df.groupby("cidade")["turistas"].sum().sort_values(ascending=False)
    reg = df.groupby("regiao")["faturamento_turismo"].sum().sort_values(ascending=False)

    c = st.columns(4)
    c[0].metric("Total de turistas", mil(df["turistas"].sum()), help=num(df["turistas"].sum()))
    c[1].metric("Faturamento total", bi(df["faturamento_turismo"].sum()),
                help=brl(df["faturamento_turismo"].sum()))
    c[2].metric("Ocupação hoteleira média", pct(df["ocupacao_hoteleira"].mean()))
    c[3].metric("Gasto médio por turista", brl(df["gasto_medio"].mean()))
    c = st.columns(4)
    c[0].metric("Cidade mais visitada", cid.index[0], f"{mil(cid.iloc[0])} turistas", delta_color="off")
    c[1].metric("Região com maior faturamento", reg.index[0], bi(reg.iloc[0]), delta_color="off")
    c[2].metric("Turistas estrangeiros", pct(df["turistas_estrangeiros"].sum() / df["turistas"].sum() * 100),
                "do total", delta_color="off")
    mov = df.groupby("regiao")["turistas"].sum().sort_values(ascending=False)
    c[3].metric("Região mais movimentada", mov.index[0], f"{mil(mov.iloc[0])} turistas", delta_color="off")

    st.subheader("Evolução mensal do número de turistas")
    m = df.groupby("periodo", as_index=False)["turistas"].sum()
    fig = px.line(m, x="periodo", y="turistas", labels={"periodo": "", "turistas": "Turistas"},
                  color_discrete_sequence=[PRIMARY])
    plotly_layout(fig)
    mostrar_plotly(fig)

    anual = df.groupby("ano")["turistas"].sum()
    txt = [f"No recorte selecionado, o Brasil recebeu {mil(anual.sum())} de turistas, "
           f"que geraram {bi(df['faturamento_turismo'].sum())} em faturamento."]
    if len(anual) > 1:
        txt.append(f"O melhor ano foi {anual.idxmax()} ({mil(anual.max())}) e o mais fraco, {anual.idxmin()} "
                   f"({mil(anual.min())}); a diferença entre eles é de {pct((anual.max() / anual.min() - 1) * 100)}, "
                   "o que mostra um turismo relativamente estável.")
    interpretacao(*txt)

    with st.expander("Qualidade e escopo dos dados"):
        st.markdown(
            f"- **{num(len(total))} registros** de {total['data'].min():%m/%Y} a {total['data'].max():%m/%Y}, "
            f"{total['cidade'].nunique()} cidades, {total['uf'].nunique()} estados e 5 regiões.\n"
            "- Sem valores nulos nem registros duplicados.\n"
            f"- Em **{num(total['inconsistente'].sum())} registros** o número de turistas estrangeiros era maior "
            "que o total de turistas. Nesses casos, os estrangeiros foram limitados ao total."
        )
    st.write(
        """
    Aluna: Marcella Guimarães Rodrigues da Silva

    Professor: Alexandre Neves Louzada
    """
    )


def pagina_temporal() -> None:
    df = CTX["df"]
    cabecalho("Evolução e sazonalidade", "Tendência anual, variação entre anos e alta temporada")

    anual = df.groupby("ano")["turistas"].sum()
    yoy = anual.pct_change() * 100

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Turistas por ano")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, anual.sort_index(), lambda v: num(v / 1e6, 1), horizontal=False, destaque=False,
               ordenar=False)
        ax.set_ylabel("milhões de turistas")
        ax.axhline(anual.mean(), color=ACCENT, ls="--", lw=1.2, label="Média anual")
        ax.legend(frameon=False)
        mostrar(fig)
    with c2:
        st.subheader("Variação em relação ao ano anterior")
        y = yoy.dropna()
        if y.empty:
            st.caption("Selecione ao menos dois anos para ver a variação anual.")
        else:
            fig, ax = plt.subplots(figsize=(6, 4))
            cores = [PRIMARY if v >= 0 else ACCENT for v in y.values]
            sns.barplot(x=y.index.astype(str), y=y.values, hue=y.index.astype(str),
                        palette=dict(zip(y.index.astype(str), cores)), legend=False, ax=ax)
            for i, v in enumerate(y.values):
                ax.text(i, v, f"{v:+.1f}%".replace(".", ","), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=9)
            ax.axhline(0, color="black", lw=0.8)
            ax.set_xlabel("")
            ax.set_ylabel("Variação (%)")
            mostrar(fig)

    st.subheader("Sazonalidade mensal")
    idx = indice_sazonal(df)
    c1, c2 = st.columns([1, 1.4])
    with c1:
        fig, ax = plt.subplots(figsize=(5, 4.2))
        s = idx.rename(index=MESES)
        cores = [ACCENT if v == idx.max() else (PRIMARY if v == idx.min() else GREY) for v in idx.values]
        sns.barplot(x=s.index, y=s.values, hue=s.index, palette=dict(zip(s.index, cores)),
                    legend=False, ax=ax)
        ax.axhline(1, color="black", lw=1, ls="--")
        ax.set_ylim(min(0.8, idx.min() - 0.05), max(1.2, idx.max() + 0.05))
        ax.set_title("Índice sazonal (1,00 = média mensal)", fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")
        mostrar(fig)
    with c2:
        piv = df.pivot_table(index="ano", columns="mes", values="turistas", aggfunc="sum") / 1e6
        piv.columns = [MESES[c] for c in piv.columns]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        sns.heatmap(piv, annot=True, fmt=".1f", cmap="YlGnBu", linewidths=0.4,
                    cbar_kws={"label": "milhões de turistas"}, annot_kws={"size": 8}, ax=ax)
        ax.set_title("Turistas por mês e ano (milhões)", fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("")
        mostrar(fig)

    pico, vale = idx.idxmax(), idx.idxmin()
    amplitude = (idx.max() - idx.min()) * 100
    forca = "fraca" if amplitude < 15 else ("moderada" if amplitude < 30 else "forte")
    interpretacao(
        f"O mês com mais turistas é **{MESES[pico]}** (índice {num(idx.max(), 2)}) e o com menos é "
        f"**{MESES[vale]}** (índice {num(idx.min(), 2)}); a amplitude entre eles é de {num(amplitude, 0)} pontos "
        f"percentuais, o que indica sazonalidade **{forca}**.",
        f"O ano de menor movimento foi {anual.idxmin()}." + (" Esse resultado coincide com a pandemia de COVID-19."
                                                           if anual.idxmin() == 2020 else ""),
    )

    st.subheader("Nível de temporada informado na base")
    temp = df.groupby("nivel_temporada")[["turistas", "ocupacao_hoteleira"]].mean().reindex(TEMPORADAS).dropna()
    fig, ax = plt.subplots(figsize=(6, 3))
    barras(ax, temp["turistas"], lambda v: num(v / 1e3, 0) + " mil", horizontal=True, destaque=True)
    ax.set_title("Média de turistas por registro", fontsize=10)
    mostrar(fig)
    if {"Alta", "Baixa"} <= set(temp.index):
        interpretacao(
            f"Os registros marcados como **Alta** temporada têm média de {num(temp.loc['Alta', 'turistas'] / 1e3, 0)} mil "
            f"turistas, contra {num(temp.loc['Baixa', 'turistas'] / 1e3, 0)} mil na **Baixa**.",
            "O rótulo de temporada não acompanha o movimento real de turistas nesta base.",
        )


def pagina_destinos() -> None:
    df = CTX["df"]
    cabecalho("Destinos turísticos", "Ranking das cidades, crescimento e perfil dos visitantes")

    por_cid = resumo(df, "cidade")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top 10 cidades mais visitadas")
        fig, ax = plt.subplots(figsize=(6, 4.5))
        barras(ax, por_cid["turistas"].nlargest(10), mil)
        mostrar(fig)
    with c2:
        st.subheader("Top 10 cidades em faturamento")
        fig, ax = plt.subplots(figsize=(6, 4.5))
        barras(ax, por_cid["faturamento"].nlargest(10), bi)
        mostrar(fig)

    top = por_cid["turistas"].nlargest(10)
    interpretacao(
        f"**{top.index[0]}** lidera o ranking de visitantes, à frente de destinos tradicionais.",
        f"A diferença entre a 1ª e a 10ª cidade é de apenas {pct((top.iloc[0] / top.iloc[-1] - 1) * 100)}, "
        "o que mostra um fluxo bem distribuído entre os destinos.",
    )

    st.subheader("Destinos com maior crescimento")
    anos = sorted(df["ano"].unique())
    if len(anos) < 2:
        st.caption("Selecione ao menos dois anos para ver o crescimento.")
    else:
        a0, a1 = anos[0], anos[-1]
        piv = df[df["ano"].isin([a0, a1])].pivot_table(index="cidade", columns="ano",
                                                         values="turistas", aggfunc="sum").dropna()
        cresc = ((piv[a1] / piv[a0] - 1) * 100).sort_values(ascending=False)
        fig = px.bar(cresc.head(10).sort_values().reset_index(name="crescimento"), x="crescimento", y="cidade",
                     orientation="h", labels={"crescimento": f"Crescimento {a0}–{a1} (%)", "cidade": ""},
                     color_discrete_sequence=[PRIMARY])
        plotly_layout(fig)
        fig.update_layout(hovermode="closest")
        mostrar_plotly(fig)
        interpretacao(
            f"Entre {a0} e {a1}, **{cresc.index[0]}** teve o maior crescimento ({pct(cresc.iloc[0])}), "
            f"enquanto **{cresc.index[-1]}** teve a maior queda ({pct(cresc.iloc[-1])})."
        )

    st.subheader("Turistas x faturamento por cidade")
    fig = px.scatter(por_cid.reset_index(), x="turistas", y="faturamento", hover_name="cidade",
                     color_discrete_sequence=[ACCENT],
                     labels={"turistas": "Total de turistas", "faturamento": "Faturamento (R$)"})
    plotly_layout(fig)
    fig.update_layout(hovermode="closest")
    mostrar_plotly(fig)
    r_tf = df["turistas"].corr(df["faturamento_turismo"])
    interpretacao(
        f"A correlação entre turistas e faturamento, registro a registro, é de **{num(r_tf, 2)}**.",
        "Receber mais turistas não significa faturar mais nesta base: o faturamento depende pouco do volume de visitantes.",
    )

    st.subheader("Ocupação hoteleira x turistas por cidade")
    fig = px.scatter(por_cid.reset_index(), x="turistas", y="ocupacao", hover_name="cidade",
                     size="faturamento", color_discrete_sequence=[PRIMARY],
                     labels={"turistas": "Total de turistas", "ocupacao": "Ocupação hoteleira média (%)"})
    plotly_layout(fig)
    fig.update_layout(hovermode="closest")
    mostrar_plotly(fig)


def pagina_regioes() -> None:
    df = CTX["df"]
    cabecalho("Regiões e mapa", "Comparação regional e distribuição geográfica do turismo")

    por_reg = resumo(df, "regiao")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Faturamento total por região")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, por_reg["faturamento"], bi, horizontal=False)
        mostrar(fig)
    with c2:
        st.subheader("Faturamento por cidade em cada região")
        fig, ax = plt.subplots(figsize=(6, 4))
        barras(ax, por_reg["faturamento_por_cidade"], bi, horizontal=False)
        mostrar(fig)

    lider = por_reg["faturamento"].idxmax()
    ultima = por_reg["faturamento"].idxmin()
    interpretacao(
        f"**{lider}** tem o maior faturamento ({bi(por_reg.loc[lider, 'faturamento'])}) e **{ultima}** o menor "
        f"({bi(por_reg.loc[ultima, 'faturamento'])}).",
        f"Porém, {lider} concentra {por_reg.loc[lider, 'cidades']} cidades na base, contra "
        f"{por_reg.loc[ultima, 'cidades']} de {ultima}. Quando o faturamento é dividido pelo número de cidades, "
        "as regiões ficam muito parecidas.",
    )

    st.subheader("Mapa do turismo por estado")
    por_uf = resumo(df, "uf").reset_index()
    por_uf["lat"] = por_uf["uf"].map(lambda u: UF_COORD[u][0])
    por_uf["lon"] = por_uf["uf"].map(lambda u: UF_COORD[u][1])
    por_uf["regiao"] = por_uf["uf"].map(df.drop_duplicates("uf").set_index("uf")["regiao"])
    fig = px.scatter_geo(por_uf, lat="lat", lon="lon", size="turistas", color="regiao", hover_name="uf",
                         color_discrete_map=REG_PAL, size_max=40,
                         hover_data={"lat": False, "lon": False, "turistas": ":,.0f"})
    fig.update_geos(scope="south america", center=dict(lat=-14, lon=-52), projection_scale=2.2,
                    showcountries=True, countrycolor="#999")
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    mostrar_plotly(fig)

    st.subheader("Resumo por região")
    tabela = por_reg[["cidades", "turistas", "faturamento", "ocupacao", "gasto_medio", "perc_estrangeiros"]].copy()
    tabela.columns = ["Cidades", "Turistas", "Faturamento (R$)", "Ocupação média (%)",
                      "Gasto médio (R$)", "Estrangeiros (%)"]
    st.dataframe(tabela.style.format({
        "Turistas": "{:,.0f}", "Faturamento (R$)": "{:,.0f}", "Ocupação média (%)": "{:.1f}",
        "Gasto médio (R$)": "{:.2f}", "Estrangeiros (%)": "{:.1f}",
    }), width="stretch")


def pagina_clima() -> None:
    df = CTX["df"]
    cabecalho("Clima e correlação", "Relação entre temperatura, eventos, ocupação e número de turistas")

    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.subheader("Temperatura x turistas")
        amostra = df.sample(min(len(df), 1500), random_state=42)
        fig = px.scatter(amostra, x="temperatura_media", y="turistas", color="regiao", opacity=0.6,
                         color_discrete_map=REG_PAL,
                         labels={"temperatura_media": "Temperatura média (°C)", "turistas": "Turistas"})
        plotly_layout(fig)
        fig.update_layout(hovermode="closest")
        mostrar_plotly(fig)
    with c2:
        st.subheader("Matriz de correlação")
        cols = ["turistas", "temperatura_media", "ocupacao_hoteleira", "eventos_realizados", "gasto_medio"]
        corr = df[cols].corr()
        fig, ax = plt.subplots(figsize=(5, 4.5))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, linewidths=0.4,
                    annot_kws={"size": 9}, ax=ax)
        ax.set_xticklabels(["Turistas", "Temperatura", "Ocupação", "Eventos", "Gasto médio"], rotation=45, ha="right")
        ax.set_yticklabels(["Turistas", "Temperatura", "Ocupação", "Eventos", "Gasto médio"], rotation=0)
        mostrar(fig)

    r = df["turistas"].corr(df["temperatura_media"])
    interpretacao(
        f"A correlação entre temperatura média e número de turistas é de **{num(r, 2)}**, praticamente zero.",
        "Ou seja, o clima não influencia o fluxo turístico nesta base. As demais variáveis também apresentam "
        "correlação próxima de zero com o número de turistas.",
    )


def pagina_tabela() -> None:
    df = CTX["df"]
    cabecalho("Tabela dinâmica", "Monte o seu próprio resumo cruzando as dimensões da base")

    dims = {"Região": "regiao", "Estado": "uf", "Cidade": "cidade", "Ano": "ano", "Mês": "mes",
            "Nível de temporada": "nivel_temporada"}
    medidas = {"Turistas": ("turistas", "sum"), "Turistas estrangeiros": ("turistas_estrangeiros", "sum"),
               "Faturamento (R$)": ("faturamento_turismo", "sum"), "Ocupação hoteleira média (%)": ("ocupacao_hoteleira", "mean"),
               "Gasto médio (R$)": ("gasto_medio", "mean"), "Eventos realizados": ("eventos_realizados", "sum")}
    c = st.columns(3)
    linhas = c[0].selectbox("Linhas", list(dims), index=0)
    colunas = c[1].selectbox("Colunas", ["(nenhuma)"] + list(dims), index=4)
    medida = c[2].selectbox("Medida", list(medidas), index=0)
    col, agg = medidas[medida]

    if colunas != "(nenhuma)" and dims[colunas] == dims[linhas]:
        st.warning("Escolha dimensões diferentes para linhas e colunas.")
        return
    piv = df.pivot_table(index=dims[linhas], columns=None if colunas == "(nenhuma)" else dims[colunas],
                         values=col, aggfunc=agg)
    if colunas == "Mês":
        piv = piv.rename(columns=MESES)
    casas = 1 if agg == "mean" else 0
    st.dataframe(piv.style.format(lambda v: num(v, casas)).background_gradient(cmap="Blues", axis=None),
                 width="stretch")
    st.download_button("Baixar tabela (CSV)", piv.to_csv().encode("utf-8"), "tabela_dinamica.csv", "text/csv")


def pagina_sql() -> None:
    df = CTX["df"]
    cabecalho("Consultas SQL", "Dados persistidos em banco SQLite com SQLAlchemy")
    st.markdown("A base tratada é salva na tabela `turismo` do arquivo `database/turismo.db`. "
                "Escolha uma consulta pronta abaixo:")

    engine = get_engine()
    consultas = {
        "Turistas e faturamento por região": """
SELECT regiao,
       COUNT(DISTINCT cidade)              AS cidades,
       SUM(turistas)                       AS turistas,
       ROUND(SUM(faturamento_turismo)/1e9, 2) AS faturamento_bi,
       ROUND(AVG(ocupacao_hoteleira), 1)   AS ocupacao_media
FROM turismo
GROUP BY regiao
ORDER BY faturamento_bi DESC""",
        "Top 10 cidades mais visitadas": """
SELECT cidade, uf, SUM(turistas) AS turistas
FROM turismo
GROUP BY cidade, uf
ORDER BY turistas DESC
LIMIT 10""",
        "Turistas por ano": """
SELECT ano, SUM(turistas) AS turistas, SUM(turistas_estrangeiros) AS estrangeiros
FROM turismo
GROUP BY ano
ORDER BY ano""",
        "Média por nível de temporada": """
SELECT nivel_temporada,
       ROUND(AVG(turistas), 0)           AS media_turistas,
       ROUND(AVG(ocupacao_hoteleira), 1) AS ocupacao_media
FROM turismo
GROUP BY nivel_temporada""",
    }
    escolha = st.selectbox("Consulta", list(consultas))
    sql = consultas[escolha].strip()
    st.code(sql, language="sql")
    st.dataframe(pd.read_sql(sql, engine), width="stretch")

    st.subheader("Dados filtrados")
    st.caption(f"{num(len(df))} registros")
    st.dataframe(df.drop(columns=["inconsistente", "periodo"]), width="stretch", height=350)
    st.download_button("Baixar dados filtrados (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "turismo_filtrado.csv", "text/csv")


def pagina_conclusao() -> None:
    df = CTX["df"]
    cabecalho("Conclusão executiva", "Respostas às perguntas orientadoras")

    por_reg = resumo(df, "regiao")
    por_cid = resumo(df, "cidade")
    idx = indice_sazonal(df)
    anual = df.groupby("ano")["turistas"].sum()
    r = df["turistas"].corr(df["temperatura_media"])

    st.subheader("Resumo")
    md(
        f"No recorte selecionado, o Brasil recebeu **{mil(df['turistas'].sum())} de turistas**, que geraram "
        f"**{bi(df['faturamento_turismo'].sum())}** em faturamento, com ocupação hoteleira média de "
        f"**{pct(df['ocupacao_hoteleira'].mean())}** e gasto médio de **{brl(df['gasto_medio'].mean())}** por turista."
    )

    st.subheader("O que os dados respondem")
    md(
        f"""
- **Cidades mais visitadas:** {', '.join(por_cid['turistas'].nlargest(3).index)}. O ranking surpreende: os destinos mais tradicionais não aparecem necessariamente no topo.
- **Alta temporada:** pico em {MESES[idx.idxmax()]} e vale em {MESES[idx.idxmin()]}, com amplitude de {num((idx.max() - idx.min()) * 100, 0)} p.p. — sazonalidade **{'fraca' if (idx.max() - idx.min()) < 0.15 else 'relevante'}**.
- **Regiões que mais movimentam recursos:** {por_reg['faturamento'].idxmax()} lidera o faturamento, principalmente por concentrar mais cidades turísticas. Por cidade, as regiões ficam equilibradas.
- **Evolução no tempo:** o turismo se manteve estável; o ano mais fraco foi {anual.idxmin()} e o mais forte, {anual.idxmax()}.
- **Clima x turismo:** correlação de {num(r, 2)} — o clima **não influencia** o fluxo de turistas.
"""
    )

    st.warning(
        "**Limitações.** A base é simulada: não há relação entre clima, eventos e número de turistas, e o "
        "rótulo de temporada não acompanha o movimento real. Os resultados mostram o método de análise; "
        "as conclusões devem ser validadas com dados reais."
    )


# ---------------------------------------------------------------- filtros e navegação
def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    sb = st.sidebar
    sb.header("Filtros")
    anos = sorted(df["ano"].unique())
    sel_ano = sb.multiselect("Ano", anos, default=anos)
    sel_mes = sb.multiselect("Mês", list(MESES), default=list(MESES), format_func=lambda m: MESES[m])
    regioes = sorted(df["regiao"].unique())
    sel_reg = sb.multiselect("Região", regioes, default=regioes)
    ufs = sorted(df.loc[df["regiao"].isin(sel_reg), "uf"].unique())
    sel_uf = sb.multiselect("Estado", ufs, default=ufs)
    cidades = sorted(df.loc[df["uf"].isin(sel_uf), "cidade"].unique())
    sel_cid = sb.multiselect("Cidade", cidades, default=cidades)
    sel_temp = sb.multiselect("Nível de temporada", TEMPORADAS, default=TEMPORADAS)

    return df[
        df["ano"].isin(sel_ano) & df["mes"].isin(sel_mes) & df["regiao"].isin(sel_reg)
        & df["uf"].isin(sel_uf) & df["cidade"].isin(sel_cid) & df["nivel_temporada"].isin(sel_temp)
    ]


def main() -> None:
    st.sidebar.markdown("### Turismo no Brasil")
    st.sidebar.caption("Projeto de Análise e Visualização de Dados com Python")

    df_all = carregar_base()
    df = aplicar_filtros(df_all)
    st.sidebar.caption(f"{num(len(df))} de {num(len(df_all))} registros selecionados")

    paginas = [
        st.Page(pagina_visao_geral, title="Visão geral", default=True),
        st.Page(pagina_temporal, title="Evolução e sazonalidade", url_path="temporal"),
        st.Page(pagina_destinos, title="Destinos turísticos", url_path="destinos"),
        st.Page(pagina_regioes, title="Regiões e mapa", url_path="regioes"),
        st.Page(pagina_clima, title="Clima e correlação", url_path="clima"),
        st.Page(pagina_tabela, title="Tabela dinâmica", url_path="tabela"),
        st.Page(pagina_sql, title="Consultas SQL", url_path="sql"),
        st.Page(pagina_conclusao, title="Conclusão executiva", url_path="conclusao"),
    ]
    pg = st.navigation(paginas)

    if df.empty:
        st.title("Turismo no Brasil")
        st.warning("Nenhum registro corresponde aos filtros selecionados. Ajuste a barra lateral.")
        st.stop()

    CTX.update(df=df, df_all=df_all)
    pg.run()


main()
