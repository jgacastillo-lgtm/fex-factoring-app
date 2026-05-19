import streamlit as st
import pandas as pd
from fpdf import FPDF
import base64
import os
from datetime import datetime
import xml.etree.ElementTree as ET

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="FEX Capital - Factoraje", layout="wide")

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
plazo_input = st.sidebar.number_input("Plazo de la Operación (Días)", min_value=1, value=30, step=1)

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
    ["Captura Manual", "Subir XML (CFDI)"],
    horizontal=True
)

df_facturas_input = pd.DataFrame()

if metodo_captura == "Captura Manual":
    st.info("Ingresa los datos directamente. Haz clic en la tabla para editar o en la última fila para agregar nuevas.")
    df_base = pd.DataFrame({"Folio": [""], "Monto ($)": [0.0]})
    df_facturas_input = st.data_editor(df_base, num_rows="dynamic", use_container_width=True, hide_index=True)
else:
    st.info("Sube uno o varios archivos XML. El sistema extraerá el Folio y Monto Total automáticamente.")
    archivos_subidos = st.file_uploader("Cargar XML", type=["xml"], accept_multiple_files=True)
    
    if archivos_subidos:
        facturas_extraidas = []
        for archivo in archivos_subidos:
            try:
                # Procesamiento del XML
                tree = ET.parse(archivo)
                root = tree.getroot()
                
                # Buscamos atributos directamente en la raíz (Comprobante)
                monto = float(root.get('Total', 0.0))
                serie = root.get('Serie', '')
                folio = root.get('Folio', '')
                folio_completo = f"{serie}{folio}".strip()
                
                if not folio_completo:
                    folio_completo = "Sin Folio"
                    
                facturas_extraidas.append({
                    "Folio": folio_completo,
                    "Monto ($)": monto
                })
            except Exception as e:
                st.error(f"Error al leer el archivo {archivo.name}: {e}")
                
        if facturas_extraidas:
            df_facturas_input = pd.DataFrame(facturas_extraidas)
            st.success(f"{len(facturas_extraidas)} factura(s) procesada(s) correctamente.")
            st.dataframe(df_facturas_input, use_container_width=True, hide_index=True)

# ==========================================
# 5. MOTOR FINANCIERO Y RESULTADOS
# ==========================================
# Limpiar datos vacíos
if not df_facturas_input.empty and "Monto ($)" in df_facturas_input.columns:
    df_facturas_input['Monto ($)'] = pd.to_numeric(df_facturas_input['Monto ($)'], errors='coerce').fillna(0)
    df_validas = df_facturas_input[df_facturas_input["Monto ($)"] > 0].copy()
    
    if not df_validas.empty:
        # Cálculos vectorizados
        df_validas['Comisión'] = df_validas['Monto ($)'] * comision_input
        df_validas['IVA Com'] = df_validas['Comisión'] * 0.16
        df_validas['Aforo'] = df_validas['Monto ($)'] * aforo_input
        
        df_validas['Monto Aforado'] = df_validas['Monto ($)'] - df_validas['Comisión'] - df_validas['IVA Com'] - df_validas['Aforo']
        
        df_validas['Intereses'] = df_validas['Monto Aforado'] * tasa_total * (plazo_input / 360)
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
        m1.metric("Valor Total de Facturas", f"{moneda} ${total_facturas:,.2f}")
        m2.metric("A Depositar Hoy", f"{moneda} ${total_depositar:,.2f}")
        m3.metric("Aforo (Devolución al Cobro)", f"{moneda} ${total_aforo:,.2f}")
        
        # Tabla detallada con formato
        st.markdown("**Detalle por Factura:**")
        format_dict = {col: "${:,.2f}" for col in df_validas.columns if col != "Folio"}
        st.dataframe(df_validas.style.format(format_dict), use_container_width=True, hide_index=True)

# ==========================================
# 6. GENERACIÓN DE PDF INSTITUCIONAL
# ==========================================
class FactorajePDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH):
            # Se bajó el logo cambiando y=10 por y=15. Sigue alineado a la izquierda (x=10).
            self.image(LOGO_PATH, x=10, y=15, w=35)
        
        # Se ajustó el inicio del título a y=42 para mantener simetría con el espacio del logo
        self.set_y(42)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(27, 27, 27) 
        self.cell(0, 6, 'Cotización de Factoraje', 0, 1, 'C')
        
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f'Fecha: {fecha_hoy} | Folio: {folio_cotizacion}', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# Botón PDF
if not df_facturas_input.empty and 'df_validas' in locals() and not df_validas.empty:
    st.markdown("---")
    if st.button("Generar y Descargar Cotización PDF"):
        pdf = FactorajePDF()
        pdf.add_page()
        pdf.set_text_color(27, 27, 27)
        
        # 1. INFORMACIÓN GENERAL
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "1. INFORMACIÓN DEL CLIENTE", ln=True, border='B')
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Cliente: {nombre_empresa}", 0, 0)
        pdf.cell(95, 7, f"RFC: {rfc_cliente}", 0, 1)
        pdf.cell(0, 7, f"Representante Legal: {representante}", 0, 1)
        pdf.cell(0, 7, f"Plazo de la Operación: {plazo_input} Días", 0, 1)
        pdf.ln(5)

        # 2. RESUMEN FINANCIERO
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "2. RESUMEN DE LA OPERACIÓN", ln=True, border='B')
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Valor Total de Facturas:", 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, f"{moneda} ${total_facturas:,.2f}", 0, 1)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Aforo (Garantía de devolución al cobro):", 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, f"{moneda} ${total_aforo:,.2f}", 0, 1)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(95, 7, f"Total a Depositar (Día 1):", 0, 0)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 7, f"{moneda} ${total_depositar:,.2f}", 0, 1)
        pdf.ln(5)

        # 3. DETALLE DE FACTURAS
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "3. DETALLE DE FACTURAS", ln=True, border='B')
        pdf.ln(3)
        
        # Encabezados de tabla
        pdf.set_fill_color(210, 210, 210)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(50, 6, "Folio", 1, 0, 'C', fill=True)
        pdf.cell(45, 6, f"Valor ({moneda})", 1, 0, 'C', fill=True)
        pdf.cell(45, 6, f"A Depositar ({moneda})", 1, 1, 'C', fill=True)
        
        # Filas de la tabla
        pdf.set_font("Arial", '', 9)
        for index, row in df_validas.iterrows():
            pdf.cell(50, 6, str(row['Folio']), 1, 0, 'C')
            pdf.cell(45, 6, f"${row['Monto ($)']:,.2f}", 1, 0, 'R')
            pdf.cell(45, 6, f"${row['A Depositar']:,.2f}", 1, 1, 'R')
        pdf.ln(10)

        # 4. NOTAS LEGALES
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, "NOTAS IMPORTANTES:", ln=True)
        pdf.cell(0, 5, "1) Esta cotización es de carácter informativo y sujeta a aprobación del Comité de Crédito de FEX Capital.", ln=True)
        pdf.cell(0, 5, f"2) Los cálculos consideran una tasa base de {tiie_input*100:.2f}% más un spread de {spread_input*100:.2f}%.", ln=True)
        pdf.cell(0, 5, "3) El aforo será devuelto al cliente una vez que la factura sea liquidada en su totalidad por el deudor.", ln=True)

        # FIRMAS
        pdf.ln(15)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(90, 10, "__________________________________", 0, 0, 'C'); pdf.cell(90, 10, "__________________________________", 0, 1, 'C')
        pdf.cell(90, 5, f"Por: {nombre_empresa}", 0, 0, 'C'); pdf.cell(90, 5, "Por: FEX CAPITAL, S.A. DE C.V.", 0, 1, 'C')
        pdf.cell(90, 5, f"{representante}", 0, 0, 'C'); pdf.cell(90, 5, "Representante Legal", 0, 1, 'C')

        # Generar descarga
        pdf_bytes = bytes(pdf.output())
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        st.markdown(f'<a href="data:application/pdf;base64,{b64_pdf}" download="Cotizacion_Factoraje_{folio_cotizacion}.pdf" style="padding:12px 20px; background-color:#0163FF; color:white; font-weight:bold; border-radius:4px; text-decoration:none; display:inline-block;">Descargar Cotización PDF</a>', unsafe_allow_html=True)
