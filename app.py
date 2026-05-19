import streamlit as st
import pandas as pd
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
    # Alineamos el logo a la izquierda en la web también
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
st.title("Calculadora de Factoraje Puro")
st.markdown("---")

with st.expander("Información General del Cliente", expanded=True):
    col1, col2 = st.columns(2)
    nombre_empresa = col1.text_input("Razón Social / Empresa", "MAREA ALIMENTOS SA DE CV")
    rfc_cliente = col1.text_input("RFC", "MAL221117ANO")
    representante = col2.text_input("Representante Legal", "Nombre del Representante")
    folio_cotizacion = col2.text_input("Folio de Cotización", "FEX-FAC-001")

# ==========================================
# 4. CAPTURA DE FACTURAS (DUAL)
# ==========================================
st.markdown("### Carga de Facturas (Borderó)")

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
    archivo_subido = st.file_uploader("Cargar Borderó", type=["csv", "xlsx"])
    if archivo_subido is not None:
        try:
            if archivo_subido.name.endswith('.csv'):
                df_facturas_input = pd.read_csv(archivo_subido)
            else:
                df_facturas_input = pd.read_excel(archivo_subido)
            st.success("Archivo procesado correctamente.")
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

# ==========================================
# 5. MOTOR FINANCIERO Y RESULTADOS
# ==========================================
# Limpiar datos vacíos
if not df_facturas_input.empty:
    df_facturas_input['Monto ($)'] = pd.to_numeric(df_facturas_input['Monto ($)'], errors='coerce').fillna(0)
    df_facturas_input['Plazo (Días)'] = pd.to_numeric(df_facturas_input['Plazo (Días)'], errors='coerce').fillna(0)
    df_validas = df_facturas_input[df_facturas_input["Monto ($)"] > 0].copy()
    
    if not df_validas.empty:
        # Cálculos vectorizados (Matemática aplicada a todas las filas a la vez)
        df_validas['Comisión'] = df_validas['Monto ($)'] * comision_input
        df_validas['IVA Com'] = df_validas['Comisión'] * 0.16
        df_validas['Aforo'] = df_validas['Monto ($)'] * aforo_input
        
        df_validas['Monto Aforado'] = df_validas['Monto ($)'] - df_validas['Comisión'] - df_validas['IVA Com'] - df_validas['Aforo']
        
        df_validas['Intereses'] = df_validas['Monto Aforado'] * tasa_total * (df_validas['Plazo (Días)'] / 360)
        df_validas['IVA Int'] = df_validas['Intereses'] * 0.16
        
        df_validas['A Depositar'] = df_validas['Monto Aforado'] - df_validas['Intereses'] - df_validas['IVA Int']
        
        st.markdown("---")
        st.markdown("### Resumen de la Operación")
        
        # Totales
        totales = df_validas.sum(numeric_only=True)
        total_facturas = totales['Monto ($)']
        total_depositar = totales['A Depositar']
        total_aforo = totales['Aforo']
        
        # Tarjetas de resumen métrico
        m1, m2, m3 = st.columns(3)
        m1.metric("Valor Total del Borderó", f"{moneda} ${total_facturas:,.2f}")
        m2.metric("A Depositar Hoy", f"{moneda} ${total_depositar:,.2f}")
        m3.metric("Aforo (Devolución al Cobro)", f"{moneda} ${total_aforo:,.2f}")
        
        # Tabla detallada con formato
        st.markdown("**Detalle por Factura:**")
        format_dict = {col: "${:,.2f}" for col in df_validas.columns if col not in ["Folio", "Plazo (Días)"]}
        st.dataframe(df_validas.style.format(format_dict), use_container_width=True, hide_index=True)
