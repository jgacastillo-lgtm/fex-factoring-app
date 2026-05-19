import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="FEX Capital - Factoraje", layout="wide", page_icon="📈")

LOGO_PATH = "LOGO_FEX.png"

# ==========================================
# 2. INTERFAZ LATERAL (PARÁMETROS)
# ==========================================
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
    st.sidebar.markdown("---")
    
st.sidebar.markdown("### Parámetros Financieros")
moneda = st.sidebar.selectbox("Moneda", ["MXN", "USD"])
tiie_input = st.sidebar.number_input("Tasa Base (TIIE/SOFR) %", min_value=0.0, value=8.50, step=0.1) / 100
spread_input = st.sidebar.number_input("Spread (Sobretasa) %", min_value=0.0, value=5.00, step=0.1) / 100
aforo_input = st.sidebar.number_input("Aforo (Garantía) %", min_value=0.0, value=13.0, step=0.5) / 100
comision_input = st.sidebar.number_input("Comisión Apertura %", min_value=0.0, value=7.0, step=0.5) / 100

tasa_total = tiie_input + spread_input

# ==========================================
# 3. DATOS GENERALES DEL CLIENTE
# ==========================================
st.title("Calculadora de Factoraje")
st.markdown("---")

with st.expander("Información General del Cliente", expanded=True):
    col1, col2 = st.columns(2)
    nombre_empresa = col1.text_input("Razón Social / Empresa", "MAREA ALIMENTOS SA DE CV")
    rfc_cliente = col1.text_input("RFC", "MAL221117ANO")
    representante = col2.text_input("Representante Legal", "Nombre del Representante")
    folio_cotizacion = col2.text_input("Folio de Cotización", "FEX-FAC-001")

# ==========================================
# 4. CAPTURA DE FACTURAS
# ==========================================
st.markdown("### Carga de Facturas")

metodo_captura = st.radio(
    "Selecciona el método de ingreso:",
    ["Captura Manual Rápida", "Subir Archivo (Excel/CSV)"],
    horizontal=True
)

df_facturas_input = pd.DataFrame()

if metodo_captura == "Captura Manual Rápida":
    st.info("Ingresa los datos directamente. Haz clic en la tabla para editar o en la última fila para agregar nuevas.")
    df_base = pd.DataFrame({"Folio": [""], "Monto ($)": [0.0], "Plazo (Días)": [30]})
    df_facturas_input = st.data_editor(df_base, num_rows="dynamic", use_container_width=True, hide_index=True)
else:
    st.info("Sube un archivo con las columnas exactas: Folio, Monto ($), Plazo (Días)")
    archivo_subido = st.file_uploader("Cargar Archivo", type=["csv", "xlsx"])
    if archivo_subido is not None:
        try:
            if archivo_subido.name.endswith('.csv'):
                df_facturas_
