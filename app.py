import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
from streamlit.components.v1 import html
import os

# --- Função de conversão DMS para Decimal ---
def dms_to_decimal(dms):
    try:
        if pd.isna(dms) or not isinstance(dms, str):
            return None
        dms = dms.strip().replace(",", ".").replace("\xa0", "").replace("\r", "").replace("\n", "")
        parts = dms.split(":")
        if len(parts) == 3:
            raw_deg = parts[0].strip()
            deg = abs(float(raw_deg))
            minu = float(parts[1].strip()) / 60
            sec = float(parts[2].strip()) / 3600
            dec = deg + minu + sec
            return -dec if "-" in raw_deg else dec
        return None
    except Exception as e:
        print(f"Erro ao converter '{dms}': {e}")
        return None

# --- Leitura e preparação dos dados ---
df = pd.read_excel("base1.xlsx", sheet_name="Folha1")
df["LATITUDE"] = df["LATITUDE"].apply(dms_to_decimal)
df["LONGITUDE"] = df["LONGITUDE"].apply(dms_to_decimal)
df.rename(columns={"MUNICÍPIO": "Municipio"}, inplace=True)
df_map = df.dropna(subset=["LATITUDE", "LONGITUDE"])

postos_unicos = df.drop_duplicates(subset=["CNPJ"])
total_postos_unicos = len(postos_unicos)
tancagem_total_geral = df["Tancagem (m³)"].sum()
tancagem_por_produto = df.groupby("Produto")["Tancagem (m³)"].sum().reset_index()
tancagem_por_mun_prod = df.groupby(["Municipio", "Produto"])["Tancagem (m³)"].sum().reset_index()

# --- Função: Mapa com cluster ---
def criar_mapa_cluster():
    m = folium.Map(location=[df_map["LATITUDE"].mean(), df_map["LONGITUDE"].mean()], zoom_start=7)
    cluster = MarkerCluster().add_to(m)
    for _, row in df_map.iterrows():
        popup = (f"<b>{row['Razão Social']}</b><br>"
                 f"Produto: {row.get('Produto', 'N/A')}<br>"
                 f"Tanque: {row.get('Nome Tanque', 'Desconhecido')}<br>"
                 f"Tancagem: {row.get('Tancagem (m³)', 0)} m³")
        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=max(5, row["Tancagem (m³)"] / 500),
            popup=popup,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6,
        ).add_to(cluster)
    return m

# --- Função: Mapa com destaque no município ---
def criar_mapa_destaque(municipio):
    m = folium.Map(location=[df_map["LATITUDE"].mean(), df_map["LONGITUDE"].mean()], zoom_start=7)
    destaque_coords = None
    for _, row in df_map.iterrows():
        cor = "green" if row["Municipio"] == municipio else "gray"
        popup = (f"<b>{row['Razão Social']}</b><br>"
                 f"Produto: {row.get('Produto', 'N/A')}<br>"
                 f"Tanque: {row.get('Nome Tanque', 'Desconhecido')}<br>"
                 f"Tancagem: {row.get('Tancagem (m³)', 0)} m³")
        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=max(5, row["Tancagem (m³)"] / 500),
            popup=popup,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.8,
        ).add_to(m)
        if row["Municipio"] == municipio:
            destaque_coords = [row["LATITUDE"], row["LONGITUDE"]]
    if destaque_coords:
        m.location = destaque_coords
        m.zoom_start = 12
    return m

# --- Interface Streamlit ---
st.set_page_config(page_title="Painel de Tancagem - Paraíba", layout="wide")

st.markdown(
    '<div style="background-color:#e0f2e9; padding:20px;">'
    '<h1 style="text-align:center; color:#004d40; font-weight:bold; font-size:36px;">Painel de Tancagem e Localização de Postos na Paraíba</h1>'
    '</div>', unsafe_allow_html=True
)
st.markdown(
    '<p style="text-align:center; font-size:18px;">'
    'O Sindalcool disponibiliza o mapeamento interativo que mostra a distribuição dos tanques de combustível e postos do estado da Paraíba, ' 
    'incluindo estatísticas por produto e por município, bem como a localização exata dos estabelecimentos.'
    '</p>', unsafe_allow_html=True
)

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div style="background-color:#28a745; padding:10px; border-radius:10px;">'
                f'<h4 style="color:#f7fafa;">Total de Postos</h4>'
                f'<h2 style="color:#f7fafa;">{total_postos_unicos}</h2>'
                '</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div style="background-color:#28a745; padding:10px; border-radius:10px;">'
                f'<h4 style="color:#f7fafa;">Tancagem Total (m³)</h4>'
                f'<h2 style="color:#f7fafa;">{int(tancagem_total_geral):,}</h2>'
                '</div>', unsafe_allow_html=True)

# Dropdown com placeholder
options = [""] + sorted(df["Municipio"].dropna().astype(str).unique().tolist())
municipio = st.selectbox("Selecione o Município para Detalhes", options, index=0)

# Mapa de destaque
st.subheader("Mapa de Postos com Destaque")
if municipio == "":
    mapa = criar_mapa_destaque(None)
else:
    mapa = criar_mapa_destaque(municipio)
html(mapa._repr_html_(), height=500)

# Info município
if municipio:
    st.subheader(f"Detalhes do Município: {municipio}")
    total_postos = df[df["Municipio"] == municipio]["CNPJ"].nunique()
    tanc_total = df[df["Municipio"] == municipio]["Tancagem (m³)"].sum()
    tanc_produto = df[df["Municipio"] == municipio].groupby("Produto")["Tancagem (m³)"].sum().reset_index()

    st.markdown(f"**Total de Postos:** {total_postos}")
    st.markdown(f"**Tancagem Total:** {int(tanc_total):,}".replace(",", "."))
    for _, row in tanc_produto.iterrows():
        valor = int(row['Tancagem (m³)'])
        st.markdown(f"- {row['Produto']}: {valor:,}".replace(",", "."))
    fig = px.bar(tanc_produto, x="Produto", y="Tancagem (m³)", title=f"Tancagem por Produto no Município de {municipio}", height=300)
    st.plotly_chart(fig, use_container_width=True)

# Mapa cluster
st.subheader("Mapa de Cluster de Tanques")
mapa_cluster = criar_mapa_cluster()
html(mapa_cluster._repr_html_(), height=500)

# Gráficos gerais
st.subheader("Gráficos Gerais")
st.plotly_chart(px.bar(tancagem_por_produto, x="Produto", y="Tancagem (m³)", title="Tancagem por Produto"), use_container_width=True)
st.plotly_chart(px.bar(tancagem_por_mun_prod, x="Municipio", y="Tancagem (m³)", color="Produto", title="Tancagem por Produto e Município"), use_container_width=True)
