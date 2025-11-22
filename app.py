# app.py

import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------
# Configuración general
# --------------------------
st.set_page_config(
    page_title="Invierte en Coyoacán",
    layout="wide",
)

# --------------------------
# Carga de datos
# --------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("data/coyoacan_clusters.parquet")

    # Fallbacks simples por si algo falta
    if "valor_estimado" not in df.columns:
        df["valor_estimado"] = df["valor_unitario_suelo"] * df["superficie_terreno"]

    if "cal_inv" not in df.columns:
        df["cal_inv"] = (df["indice_inversion"] * 10).round(1)

    return df

df = load_data()

required_cols = [
    "latitud", "longitud",
    "categoria_cluster", "cluster_humano",
    "valor_unitario_suelo", "density",
    "indice_inversion", "antiguedad_norm",
    "superficie_terreno", "superficie_construccion",
    "colonia", "alcaldia", "valor_estimado",
    "cal_inv",
]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Faltan columnas en el dataset: {missing}")
    st.stop()

# --------------------------
# Descripciones cortas por categoría (para texto arriba, no hover)
# --------------------------
descripciones_categoria = {
    "Pequeño en zona de pusvalía media-alta":
        "Ideal para renta compacta en zonas con buena demanda.",
    "Antiguo con espacio para construcción":
        "Perfecto para remodelar y ampliar, con buena plusvalía.",
    "Conjunto habitacional grande":
        "Excelente base para proyectos residenciales a escala.",
    "Moderno pequeña en zona media":
        "Buena opción para renta estable o primera vivienda.",
    "Pequeño en zona de alta plusvalía":
        "Ubicación top para renta pequeña de alto valor.",
    "Grande y antiguo":
        "Oportunidad para renovación profunda y gran valor de reventa.",
    "Moderno en zona de alta plusvalía":
        "Listo para habitar o rentar sin casi invertir.",
    "Grande de alta plusvalía":
        "Actualiza acabados y capitaliza la ubicación privilegiada.",
    "Pequeño antiguo en zona de alta plusvalía":
        "Ideal para una renovación focalizada con buen retorno.",
    "Mediano en zona de pusvalía media":
        "Con mejoras ligeras puedes aumentar su valor.",
}

# --------------------------
# Encabezado
# --------------------------
st.title("Invierte en Coyoacán")
st.caption(
    "¿Viste una propiedad de tu interés? Descubre su clasificación y score de índice de inversión a partir de la información catastral"
)

# --------------------------
# Sidebar – Filtros
# --------------------------
st.sidebar.header("Filtra tu búsqueda")

# 1) MULTISELECT de categorías
categorias = sorted(df["categoria_cluster"].dropna().unique())
categorias_sel = st.sidebar.multiselect(
    "1. Tipo de predio (una o varias categorías)",
    options=categorias,
    default=categorias,
)

# 2) Filtro de presupuesto aproximado
presupuesto_opciones = {
    "Cualquier presupuesto": (None, None),
    "Hasta $1M": (0, 1_000_000),
    "$1M - $3M": (1_000_000, 3_000_000),
    "$3M - $5M": (3_000_000, 5_000_000),
    "Más de $5M": (5_000_000, None),
}
presupuesto_sel = st.sidebar.selectbox(
    "2. Valor catastral estimado", list(presupuesto_opciones.keys())
)
pres_min, pres_max = presupuesto_opciones[presupuesto_sel]

# Dataset previo para calcular colonias disponibles
df_pre = df.copy()

if categorias_sel:
    df_pre = df_pre[df_pre["categoria_cluster"].isin(categorias_sel)]

if pres_min is not None:
    df_pre = df_pre[df_pre["valor_estimado"] >= pres_min]
if pres_max is not None:
    df_pre = df_pre[df_pre["valor_estimado"] <= pres_max]

colonias_disponibles = sorted(df_pre["colonia"].dropna().unique())

# 3) MULTISELECT de colonias
colonias_sel = st.sidebar.multiselect(
    "3. Colonias",
    options=colonias_disponibles,
    default=colonias_disponibles,
)

# --------------------------
# Aplicar todos los filtros al dataset principal
# --------------------------
df_f = df.copy()

if categorias_sel:
    df_f = df_f[df_f["categoria_cluster"].isin(categorias_sel)]

if pres_min is not None:
    df_f = df_f[df_f["valor_estimado"] >= pres_min]
if pres_max is not None:
    df_f = df_f[df_f["valor_estimado"] <= pres_max]

if colonias_sel:
    df_f = df_f[df_f["colonia"].isin(colonias_sel)]

# --------------------------
# KPIs
# --------------------------
col1, col2, col3 = st.columns(3)

total_predios = len(df_f)
num_categorias = df_f["categoria_cluster"].nunique()
valor_mediano_m2 = df_f["valor_unitario_suelo"].median() if total_predios > 0 else 0

col1.metric("Predios", f"{total_predios:,}")
col2.metric("Categorías presentes", f"{num_categorias}")
col3.metric("Valor por m² (mediana)", f"${valor_mediano_m2:,.0f}")

st.markdown("---")

# --------------------------
# Texto de categorías seleccionadas
# --------------------------
if categorias_sel and len(categorias_sel) == 1:
    cat = categorias_sel[0]
    st.subheader(f"Clasificación seleccionada: {cat}")
    desc = descripciones_categoria.get(
        cat,
        "Esta clasificación agrupa propiedades con características similares de ubicación, tamaño y potencial.",
    )
    st.write(desc)
elif categorias_sel and len(categorias_sel) > 1:
    st.subheader("Estás explorando varias clasificaciones de propiedades")
    st.write("Categorías seleccionadas:")
    st.write(", ".join(categorias_sel))
else:
    st.subheader("Explora las diferentes clasificaciones de propiedades en Coyoacán")

# --------------------------
# Mapa principal
# --------------------------
st.markdown("### Mapa interactivo de propiedades")

if df_f.empty:
    st.warning(
        "No hay propiedades que cumplan los filtros seleccionados. Ajusta los filtros para ver resultados."
    )
else:
    df_f = df_f.copy()
    df_f["cal_inv_str"] = df_f["cal_inv"].round(1).astype(str)

    fig_map = px.scatter_mapbox(
        df_f,
        lat="latitud",
        lon="longitud",
        color="categoria_cluster",
        custom_data=[
            "cal_inv_str",          # 0 → score
            "superficie_terreno",   # 1
            "superficie_construccion",  # 2
        ],
        zoom=12,
        height=600,
        opacity=0.85,
    )

    fig_map.update_traces(
        hovertemplate=(
            "<b style='font-size:22px'>%{customdata[0]}</b><br>"   # Score grande
            "Terreno: %{customdata[1]:,.0f} m²<br>"
            "Construcción: %{customdata[2]:,.0f} m²"
            "<extra></extra>"
        ),
        marker=dict(size=8),
        showlegend=False,
    )

    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
        showlegend=False,
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_color="black",
        ),
    )

    st.plotly_chart(fig_map, use_container_width=True)

# --------------------------
# Tabla resumen por categoría y colonia
# --------------------------
st.markdown("### Resumen por categoría y colonia (según filtros actuales)")

if df_f.empty:
    st.info("No hay datos para mostrar el resumen. Ajusta los filtros.")
else:
    resumen = (
        df_f
        .groupby(["categoria_cluster", "colonia"])
        .agg(
            n_predios=("colonia", "size"),
            terreno_mediana=("superficie_terreno", "median"),
            construccion_mediana=("superficie_construccion", "median"),
            cal_inv_media=("cal_inv", "mean"),
        )
        .reset_index()
        .sort_values("cal_inv_media", ascending=False)
    )

    resumen = resumen.rename(columns={
        "categoria_cluster": "Categoría",
        "colonia": "Colonia",
        "n_predios": "Predios",
        "terreno_mediana": "Terreno (m²) (mediana)",
        "construccion_mediana": "Construcción (m²) (mediana)",
        "cal_inv_media": "Score inversión (promedio 0–10)",
    })

    st.dataframe(
        resumen.style.format(
            {
                "Terreno (m²) (mediana)": "{:,.0f}",
                "Construcción (m²) (mediana)": "{:,.0f}",
                "Score inversión (promedio 0–10)": "{:.1f}",
            }
        ),
        use_container_width=True,
    )
