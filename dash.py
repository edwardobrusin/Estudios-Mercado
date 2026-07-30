import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os
import urllib.request
import json
import jenkspy
import textwrap
from streamlit_javascript import st_javascript

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA (FULL CANVAS)
# ==========================================
st.set_page_config(
    page_title="Tablero Manufacturero | NAFIN - BANCOMEXT",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" # Ocultamos el sidebar por defecto
)

# Estilos CSS Avanzados - Identidad Institucional y Full Width
st.markdown("""
<style>
    /* Remover márgenes y padding para usar toda la pantalla */
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    /* Espacio de seguridad extra para que el selectbox no quede tapado por el header de Streamlit */
    div[data-testid="stSelectbox"] {
        margin-top: 0.4rem;
    }
    .stApp {
        background-color: #F8FAFC;
    }
    /* Estilo del UpBar */
    .upbar-container {
        background-color: #ffffff;
        border: 1px solid #E2E8F0;
        padding: 15px 25px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        margin-bottom: 15px;
    }
    h1, h2, h3 { color: #0F172A !important; font-weight: 800 !important; letter-spacing: -0.5px; }
    * { font-family: 'Noto Sans', sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.1 DETECCIÓN DE ANCHO DISPONIBLE (RESPONSIVE)
# ==========================================
ANCHO_REFERENCIA = 1600  # px: ancho de monitor sobre el cual se calibró el diseño original

ancho_pantalla = st_javascript("window.innerWidth")
if not ancho_pantalla:
    ancho_pantalla = ANCHO_REFERENCIA  # fallback mientras se resuelve el valor real (primer render)

factor_escala = ancho_pantalla / ANCHO_REFERENCIA
factor_escala = max(0.55, min(1.0, factor_escala))  # nunca crece más allá del diseño original

def wrap_dinamico(texto, fraccion_ancho, tam_fuente):
    """Inserta <br> automáticos según el espacio real (px) disponible para esa caja."""
    ancho_caja_px = ancho_pantalla * fraccion_ancho
    caracteres_por_linea = max(20, int(ancho_caja_px / (tam_fuente * 0.55)))
    return "<br>".join(textwrap.wrap(texto, width=caracteres_por_linea))

# ==========================================
# 2. CARGA Y TRANSFORMACIÓN DE DATOS
# ==========================================
@st.cache_data
def load_data():
    # En un entorno real, lee de la carpeta data: 
    # pd.read_excel("data/scian.xlsx"), etc.
    try:
        df_scian = pd.read_excel("data/scian.xlsx")
        df_ue = pd.read_excel("data/ue.xlsx")
        df_tend = pd.read_excel("data/tendencia.xlsx")
        df_tip = pd.read_excel("data/tipificacion.xlsx")
        df_imports = pd.read_excel("data/imports.xlsx")
        df_ied = pd.read_excel("data/ied.xlsx")
    except Exception as e:
        st.error(f"Error cargando archivos: {e}. Asegúrate de que scian.xlsx, ue.xlsx y tendencia.xlsx existan en la carpeta 'data'.")
        st.stop()

    # --- PROCESAMIENTO UE ---
    df_ue['codigo_act'] = df_ue['codigo_act'].astype(str)
    # Extraer 4 dígitos (Rama)
    df_ue['Rama'] = df_ue['codigo_act'].str[:4]
    # Filtrar solo Manufactura (inician con 31 o 33)
    df_ue = df_ue[df_ue['Rama'].str.startswith('31') | df_ue['Rama'].str.startswith('33')]

    # --- PROCESAMIENTO TENDENCIA ---
    df_tend['Rama'] = df_tend['Rama'].astype(str)
    df_tend = df_tend[df_tend['Rama'].str.startswith('31') | df_tend['Rama'].str.startswith('33')]
    df_tend = df_tend[df_tend['Año'] >= 2018]
    df_tend['Periodo'] = df_tend['Año'].astype(str) + " T" + df_tend['Trimestre'].astype(str)
    
    df_tip['Rama'] = df_tip['Rama'].astype(str)

    # --- PROCESAMIENTO SCIAN ---
    df_scian['Rama'] = df_scian['Rama'].astype(str)
    # Obtener diccionario único de Ramas manufactureras para el selectbox
    cat_ramas = df_scian[df_scian['Rama'].str.startswith('31') | df_scian['Rama'].str.startswith('33')]
    cat_ramas = cat_ramas[['Rama', 'N_Rama']].drop_duplicates()
    
    return df_ue, df_tend, cat_ramas, df_tip, df_imports, df_ied

df_ue, df_tend, cat_ramas, df_tip, df_imports, df_ied = load_data()

# Normalizador de estados (Mismo usado en ficha_v4 para coincidir con el GeoJSON)
NAME_NORMALIZER = {
    'Aguascalientes': 'Aguascalientes',
    'Baja california': 'Baja California',
    'Baja california sur': 'Baja California Sur',
    'Campeche': 'Campeche',
    'Chiapas': 'Chiapas',
    'Chihuahua': 'Chihuahua',
    'Ciudad de méxico': 'Ciudad de México',
    'Coahuila de zaragoza': 'Coahuila',
    'Colima': 'Colima',
    'Durango': 'Durango',
    'Guanajuato': 'Guanajuato',
    'Guerrero': 'Guerrero',
    'Hidalgo': 'Hidalgo',
    'Jalisco': 'Jalisco',
    'Michoacán de ocampo': 'Michoacán',
    'Morelos': 'Morelos',
    'México': 'México',
    'Nayarit': 'Nayarit',
    'Nuevo león': 'Nuevo León',
    'Oaxaca': 'Oaxaca',
    'Puebla': 'Puebla',
    'Querétaro': 'Querétaro',
    'Quintana roo': 'Quintana Roo',
    'San luis potosí': 'San Luis Potosí',
    'Sinaloa': 'Sinaloa',
    'Sonora': 'Sonora',
    'Tabasco': 'Tabasco',
    'Tamaulipas': 'Tamaulipas',
    'Tlaxcala': 'Tlaxcala',
    'Veracruz de ignacio de la llave': 'Veracruz',
    'Yucatán': 'Yucatán',
    'Zacatecas': 'Zacatecas',
    # Mantenemos las variaciones anteriores por seguridad
    'Coahuila de Zaragoza': 'Coahuila', 
    'Michoacán de Ocampo': 'Michoacán', 
    'Veracruz de Ignacio de la Llave': 'Veracruz', 
    'Estado de México': 'México',
    'Mexico': 'México',
    'veracruz': 'Veracruz'
}

# ==========================================
# 3. FILTRO SUPERIOR
# ==========================================
# Crear diccionario para mostrar Nombre pero filtrar por Código
opciones_rama = {f"{row['Rama']} - {row['N_Rama']}": row['Rama'] for _, row in cat_ramas.iterrows()}

rama_seleccionada_txt = st.selectbox(
    "Filtro por Rama Industrial:", 
    options=list(opciones_rama.keys()),
    index=0,
    label_visibility="collapsed"
)
rama_filtro = opciones_rama[rama_seleccionada_txt]

# ==========================================
# 4. FILTRADO DINÁMICO DE DATOS
# ==========================================
# Filtrar df por la rama seleccionada
ue_filt = df_ue[df_ue['Rama'] == rama_filtro].copy()
tend_filt = df_tend[df_tend['Rama'] == rama_filtro].copy()

# A. Datos Mapa: Agrupar por estado y sumar p_o_est
ue_filt['entidad_norm'] = ue_filt['entidad'].replace(NAME_NORMALIZER)
df_mapa = ue_filt.groupby('entidad_norm')['p_o_est'].sum().reset_index()

# B. Datos Pastel: Agrupar por estrato y sumar unidades económicas (ue)
df_pastel = ue_filt.groupby('estrato')['ue'].sum().reset_index()

# C. Extracción de Tipificación
tip_val = df_tip[df_tip['Rama'] == rama_filtro]['Tipificación'].values
texto_tipificacion = tip_val[0] if len(tip_val) > 0 else "Sin tipificación"
texto_tipificacion = wrap_dinamico(texto_tipificacion, fraccion_ancho=0.42, tam_fuente=16)

# D. Procesamiento Importaciones
df_imports['scian'] = df_imports['scian'].astype(str)
imp_filt = df_imports[df_imports['scian'] == rama_filtro].copy()
if not imp_filt.empty:
    imp_filt = imp_filt.sort_values('fecha')

# E. Procesamiento IED
df_ied['scian'] = df_ied['scian'].astype(str)

def procesar_ied(codigo_scian):
    df_temp = df_ied[df_ied['scian'] == codigo_scian].copy()
    if df_temp.empty: return None, None, None, False
    
    # 1. Stock 2018-2025 (4T)
    df_stock = df_temp[(df_temp['trimestre'] == 'T4') & (df_temp['año'] >= 2018) & (df_temp['año'] <= 2025)]
    
    # Validar suficiencia de datos (Mínimo 5 datos válidos en el stock)
    validos = sum(1 for val in df_stock['valor'] if str(val).strip().upper() != 'C' and pd.notna(val))
    if validos < 5:
        return None, None, None, False
        
    x_vals, y_vals, hover_vals = [], [], []
    
    for anio in range(2018, 2026):
        x_vals.append(str(anio))
        fila = df_stock[df_stock['año'] == anio]
        if not fila.empty:
            val = fila['valor'].values[0]
            if str(val).strip().upper() == 'C' or pd.isna(val):
                y_vals.append(0) # Se usa 0 para que plotly no omita el espacio en el eje
                hover_vals.append("Dato testado (C)")
            else:
                y_vals.append(float(val))
                hover_vals.append(f"IED: ${float(val):,.1f}")
        else:
            y_vals.append(0)
            hover_vals.append("Dato no disponible")
            
    # 2. Comparativa 2026 (Mismo trimestre)
    df_2026 = df_temp[df_temp['año'] == 2026].copy()
    if not df_2026.empty:
        ult_trim = df_2026['trimestre'].max()
        val_2026 = df_2026[df_2026['trimestre'] == ult_trim]['valor'].values[0]
        
        fila_2025 = df_temp[(df_temp['año'] == 2025) & (df_temp['trimestre'] == ult_trim)]
        val_2025 = fila_2025['valor'].values[0] if not fila_2025.empty else 'C'
        
        es_val_2026 = str(val_2026).strip().upper() != 'C' and pd.notna(val_2026)
        es_val_2025 = str(val_2025).strip().upper() != 'C' and pd.notna(val_2025)
        
        if es_val_2026 and es_val_2025:
            # Se agrega un string vacío como separador visual (con valor None para que no dibuje barra) y luego los dos trimestres
            x_vals.extend([" ", f"{ult_trim} 2025", f"{ult_trim} 2026"])
            y_vals.extend([None, float(val_2025), float(val_2026)])
            hover_vals.extend(["", f"IED: ${float(val_2025):,.1f}", f"IED: ${float(val_2026):,.1f}"])
            
    return x_vals, y_vals, hover_vals, True

x_ied, y_ied, hover_ied, es_valido_ied = procesar_ied(rama_filtro)
nivel_ied = "Rama"

if not es_valido_ied:
    # Retroceder a Subsector (3 dígitos) si la rama falla la regla de disponibilidad
    subsector = rama_filtro[:3]
    x_ied, y_ied, hover_ied, es_valido_ied = procesar_ied(subsector)
    nivel_ied = f"Subsector {subsector}"

# ==========================================
# 5. CREACIÓN DEL LIENZO ÚNICO (PLOTLY CANVAS)
# ==========================================
# Cargar GeoJSON para el mapa
@st.cache_data
def get_geojson():
    url = "https://raw.githubusercontent.com/angelnmara/geojson/master/mexicoHigh.json"
    req = urllib.request.urlopen(url)
    return json.loads(req.read())

geojson_mx = get_geojson()

# D. Jenks (Natural Breaks) para el mapa y Top 5
if len(df_mapa[df_mapa['p_o_est'] > 0]) > 5:
    breaks = jenkspy.jenks_breaks(df_mapa[df_mapa['p_o_est'] > 0]['p_o_est'], 5)
else:
    breaks = [0, 1, 2, 3, 4, 5]

def get_jenks_category(val):
    if pd.isna(val) or val <= 0: return 0
    if val <= breaks[1]: return 1
    elif val <= breaks[2]: return 2
    elif val <= breaks[3]: return 3
    elif val <= breaks[4]: return 4
    else: return 5
    
todos_estados = [f['properties']['name'] for f in geojson_mx['features']]
df_mapa_full = pd.DataFrame({'entidad_norm': todos_estados})
df_mapa_full = df_mapa_full.merge(df_mapa, on='entidad_norm', how='left').fillna({'p_o_est': 0})
df_mapa_full['cat_jenks'] = df_mapa_full['p_o_est'].apply(get_jenks_category)

# Preparar etiquetas de la leyenda (Colorbar)
rango_labels = ["N/A"] + [f"{int(breaks[i])+1 if i>0 else int(breaks[0]):,.0f} - {int(breaks[i+1]):,.0f}" for i in range(5)]

# Top 5 para la anotación
total_nacional = df_mapa['p_o_est'].sum()
top5 = df_mapa.sort_values('p_o_est', ascending=False).head(5)
top5_html = "<b>Top 5 Entidades:</b><br><br>"
for i, row in top5.iterrows():
    pct = (row['p_o_est'] / total_nacional * 100) if total_nacional > 0 else 0
    top5_html += f"• {row['entidad_norm']}: {row['p_o_est']:,.0f} ({pct:.1f}%)<br>"

# Footnote con salto de línea automático y ancho máximo controlado
texto_footer_raw = ("Fuente: Elaborado por Nafin-Bancomext con información del INEGI. 1/ Para más detalles, véase anexo "
                     "metodológico. 2/ Cálculos mediante estimación de personas ocupadas por estado con el Directorio "
                     "Estadístico Nacional de Unidades Económicas, de acuerdo con los siguientes rangos. 0 a 5 personas: 2.5 | "
                     "6 a 10 personas: 8 | 11 a 30 personas: 20.5 | 31 a 50 personas: 40.5 | 51 a 100 personas: 75.5 | "
                     "101 a 250 personas: 175.5 | 251 y más personas: 500.")
texto_footer = wrap_dinamico(texto_footer_raw, fraccion_ancho=0.90, tam_fuente=10)

# Cálculo dinámico del eje Y de barras

# --- LEYENDA DISCRETA: cuadros individuales por rango (sustituye la colorbar combinada) ---
colores_leyenda = ['#d3d3d3', '#feebe2', '#fbb4b9', '#f768a1', '#c51b8a', '#7a0177']
legend_shapes = []
legend_annotations = []
y0_legend = 0.35
paso_legend = 0.045
for color, label in zip(colores_leyenda, rango_labels):
    legend_shapes.append(dict(
        type="rect", xref="paper", yref="paper",
        x0=0.35, x1=0.37, y0=y0_legend, y1=y0_legend + 0.03,
        fillcolor=color, line=dict(color="white", width=1)
    ))
    legend_annotations.append(dict(
        x=0.375, y=y0_legend + 0.015, xref="paper", yref="paper",
        text=label, showarrow=False, font=dict(size=14 * factor_escala, color="#0F172A"),
        align="left", xanchor="left", yanchor="middle"
    ))
    y0_legend -= paso_legend

# Cálculo dinámico del eje Y de barras
y_min_bar = tend_filt['Valor'].min()
y_max_bar = tend_filt['Valor'].max()
margen_y = (y_max_bar - y_min_bar) * 0.1
if margen_y == 0: margen_y = y_max_bar * 0.1
rango_y = [max(0, y_min_bar - margen_y), y_max_bar + margen_y]

# Inicializar Figura
fig = go.Figure()

# Colores discretos Plotly (0=Gris, 1-5=Paleta Rosa/Morada)
custom_colorscale = [
    [0.0, '#d3d3d3'], [0.1, '#d3d3d3'], # 0 (N/A)
    [0.1, '#feebe2'], [0.3, '#feebe2'], # 1
    [0.3, '#fbb4b9'], [0.5, '#fbb4b9'], # 2
    [0.5, '#f768a1'], [0.7, '#f768a1'], # 3
    [0.7, '#c51b8a'], [0.9, '#c51b8a'], # 4
    [0.9, '#7a0177'], [1.0, '#7a0177']  # 5
]

# --- 1. AGREGAR MAPA (Right, Top) ---
fig.add_trace(go.Choropleth(
    geojson=geojson_mx,
    locations=df_mapa_full['entidad_norm'],
    featureidkey='properties.name',
    z=df_mapa_full['cat_jenks'],
    customdata=df_mapa_full['p_o_est'],
    hovertemplate="<b>%{location}</b><br>Pers. Ocupadas: %{customdata:,.0f}<extra></extra>",
    colorscale=custom_colorscale,
    zmin=0, zmax=5,
    marker_line_color='white',
    marker_line_width=0.5,
    showscale=False,
    geo="geo"
))

# --- 2. AGREGAR GRÁFICA DE BARRAS TENDENCIA (Bottom-Left) ---
fig.add_trace(go.Bar(
    x=tend_filt['Periodo'],
    y=tend_filt['Valor'],
    marker_color="#c51b8a", 
    xaxis="x",
    yaxis="y",
    name="Tendencia",
    hovertemplate="<b>%{x}</b><br>Valor: %{y:,.0f}<extra></extra>"
))

# --- 3. AGREGAR GRÁFICA DE PASTEL (Bottom-Right) ---
colores_estrato = {'Micro': '#feebe2', 'Pequeña': '#fbb4b9', 'Mediana': '#f768a1', 'Grande': '#7a0177'}
fig.add_trace(go.Pie(
    labels=df_pastel['estrato'],
    values=df_pastel['ue'],
    marker=dict(colors=[colores_estrato.get(x, '#d3d3d3') for x in df_pastel['estrato']], line=dict(color='white', width=1)),
    textinfo='label+percent',
    hovertemplate="%{label}<br>UEs: %{value:,.0f} (%{percent})<extra></extra>",
    hole=0.4,
    domain=dict(x=[0.77, 0.99], y=[0.45, 0.85]) 
))

# --- 4. AGREGAR GRÁFICA IMPORTACIONES (Top-Left) ---
if not imp_filt.empty:
    fig.add_trace(go.Scatter(
        x=imp_filt['fecha'],
        y=imp_filt['valor'],
        mode='lines',
        fill='tozeroy',
        marker_color="#f768a1",
        xaxis="x2",
        yaxis="y2",
        name="Importaciones",
        hovertemplate="<b>%{x}</b><br>Valor: $%{y:,.0f}<extra></extra>"
    ))

# --- 5. AGREGAR GRÁFICA IED (Top-Right) ---
if es_valido_ied:
    fig.add_trace(go.Bar(
        x=x_ied,
        y=y_ied,
        customdata=hover_ied,
        marker_color="#7a0177",
        xaxis="x3",
        yaxis="y3",
        name="IED",
        hovertemplate="<b>%{x}</b><br>%{customdata}<extra></extra>"
    ))

# --- 6. CONFIGURAR LAYOUT Y ANOTACIONES ---
try:
    bg_img = Image.open("images/background.png")
    fig.add_layout_image(
        dict(
            source=bg_img,
            xref="paper", yref="paper",
            x=0, y=1,
            sizex=1, sizey=1,
            sizing="stretch",
            opacity=1.0,
            layer="below"
        )
    )
except Exception as e: pass

fig.update_layout(
    width=1921, # 50% de 3842 para bloquear el aspect ratio visualmente
    height=1081, # 50% de 2162
    margin=dict(l=0, r=0, t=0, b=80), # Aumentamos el margen inferior para que quepa el texto multilínea
    showlegend=False,
    font=dict(family="Noto Sans", color="#0F172A"),
    
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    
    # --- DOMINIO DEL MAPA (geo) - CENTER ---
    geo=dict(
        domain=dict(x=[0.205, 0.80], y=[0.00, 0.90]),
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)"
    ),
    
    # --- DOMINIO DE BARRAS TENDENCIA (x, y) - BOTTOM LEFT ---
    xaxis=dict(
        domain=[0.03, 0.27], 
        anchor="y", 
        showgrid=False, 
        tickfont=dict(size=9)
    ),
    yaxis=dict(
        domain=[0.55, 0.80],
        anchor="x", 
        showgrid=True, 
        gridcolor="rgba(0,0,0,0.1)",
        range=rango_y
    ),
    
    # --- DOMINIO DE IMPORTACIONES (x2, y2) - TOP LEFT ---
    xaxis2=dict(
        domain=[0.77, 0.99], 
        anchor="y2", 
        showgrid=False, 
        tickfont=dict(size=9)
    ),
    yaxis2=dict(
        domain=[0.1, 0.40],
        anchor="x2", 
        showgrid=True, 
        gridcolor="rgba(0,0,0,0.1)"
    ),

    # --- DOMINIO DE IED (x3, y3) - TOP RIGHT ---
    xaxis3=dict(
        domain=[0.03, 0.27], 
        anchor="y3", 
        showgrid=False, 
        tickfont=dict(size=10),
        type="category"
    ),
    yaxis3=dict(
        domain=[0.1, 0.45],
        anchor="x3", 
        showgrid=True, 
        gridcolor="rgba(0,0,0,0.1)"
    ),

    annotations=[
        # Título superior izquierdo "Codigo - Descripción"
        dict(x=0.02, y=0.98, xref="paper", yref="paper", text=f"<b>{rama_seleccionada_txt}</b>", showarrow=False, font=dict(size=26 * factor_escala, color="#0F172A"), align="left", xanchor="left"),
        
        # Títulos de las gráficas
        dict(x=0.02, y=0.85, xref="paper", yref="paper", text="Tendencia de largo plazo<sup>1/</sup>", showarrow=False, font=dict(size=18 * factor_escala, weight="bold", color="#0F172A"), align="left", xanchor="left"),
        dict(x=0.75, y=0.42, xref="paper", yref="paper", text="Importaciones mensuales EUA", showarrow=False, font=dict(size=18 * factor_escala, weight="bold", color="#0F172A"), align="left", xanchor="left"),
        dict(x=0.75, y=0.90, xref="paper", yref="paper", text="Distribución de UEs por estrato", showarrow=False, font=dict(size=18 * factor_escala, weight="bold", color="#0F172A"), align="left", xanchor="left"),
        dict(x=0.02, y=0.46, xref="paper", yref="paper", text=f"Inversión Extranjera Directa ({nivel_ied})", showarrow=False, font=dict(size=18 * factor_escala, weight="bold", color="#0F172A"), align="left", xanchor="left"),
        dict(x=0.48, y=0.85, xref="paper", yref="paper", text="Personal ocupado estimado<sup>2/</sup>", showarrow=False, font=dict(size=22 * factor_escala, weight="bold", color="#0F172A"), align="center", xanchor="center"),
        
        # Cuadro Top 5 Entidades (Ajustado al centro/mapa)
        dict(x=0.56, y=0.68, xref="paper", yref="paper", text=top5_html, showarrow=False, font=dict(size=16 * factor_escala, color="#0F172A"), align="left", xanchor="left", yanchor="middle", bgcolor="rgba(255,255,255,0.92)", bordercolor="#c51b8a", borderwidth=1.5, borderpad=10 * factor_escala),
        
        # Cuadro Tipificación (Debajo del mapa)
        dict(x=0.25, y=0.88, xref="paper", yref="paper", text=f"<b>Tipificación tendencia: 2018-2026 <sup>1/</sup></b><br>{texto_tipificacion}", showarrow=False, font=dict(size=14 * factor_escala, color="#7a0177"), align="center", xanchor="center", bgcolor="#feebe2", bordercolor="#c51b8a", borderwidth=2, borderpad=10 * factor_escala),
        
        # Condicional si Imports está vacío
        *( [dict(x=0.135, y=0.70, xref="paper", yref="paper", text="No se reportaron importaciones de<br>Estados Unidos originarias<br>de México para esta rama.", showarrow=False, font=dict(size=11, color="#DC2626"), align="center", xanchor="center", bgcolor="white", bordercolor="#E2E8F0", borderwidth=1, borderpad=8)] if imp_filt.empty else [] ),
        
        # Condicional si IED está vacío
        *( [dict(x=0.865, y=0.70, xref="paper", yref="paper", text="Datos de IED no disponibles<br>por criterio de confidencialidad.", showarrow=False, font=dict(size=11, color="#DC2626"), align="center", xanchor="center", bgcolor="white", bordercolor="#E2E8F0", borderwidth=1, borderpad=8)] if not es_valido_ied else [] ),

        # Pie de página (Footer) - usa el texto ya envuelto dinámicamente según ancho real de pantalla
        dict(x=0.01, y=0.00, xref="paper", yref="paper", text=texto_footer, showarrow=False, font=dict(size=10 * factor_escala, color="#64748B"), align="left")
    ] + legend_annotations,
    shapes=legend_shapes
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})