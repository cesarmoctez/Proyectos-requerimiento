import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuración de la interfaz de Streamlit
st.set_page_config(page_title="Comparador de Costos Operativos", layout="wide")

st.title("📊 Estructurador de Costos de Personal y Tercerización")
st.write("Control total de variables de nómina, cálculo de tiempo extra y curvas de sensibilidad financiera.")

st.markdown("---")

# --- BARRA LATERAL: CONTROL TOTAL DE VARIABLES ---
st.sidebar.header("📋 1. Datos de la Actividad")
tarea = st.sidebar.text_input("Nombre de la tarea / Actividad", value="Montaje de Estructura Metálica")
horas_vendidas = st.sidebar.number_input("Horas totales del proyecto", min_value=1, value=240, step=10)
dias_meta = st.sidebar.number_input("Días Meta (Plazo del proyecto)", min_value=1, value=10, step=1)
jornada_diaria = st.sidebar.number_input("Jornada Diaria Regular (hrs)", min_value=1, value=8, step=1)

st.sidebar.header("👥 2. Plantilla Local")
trabajadores_locales = st.sidebar.number_input("Cantidad de Personal Local", min_value=1, value=4, step=1)
factor_tiempo_extra = st.sidebar.slider("Factor de Pago de Hora Extra (LFT)", min_value=1.5, max_value=3.0, value=2.0, step=0.5)

# Sección expandible para control absoluto de la nómina
st.sidebar.markdown("---")
with st.sidebar.expander("💰 3. Configuración de Nómina Base", expanded=True):
    st.write("_Valores de referencia para el equipo total por el periodo del proyecto_")
    input_salario_base = st.number_input("Salario Base ($)", min_value=0.0, value=27742.0, step=500.0)
    input_variables = st.number_input("Variables / Bonos ($)", min_value=0.0, value=175.0, step=50.0)
    input_provisiones = st.number_input("Provisiones de Ley (Finiquito) ($)", min_value=0.0, value=3971.0, step=100.0)
    input_prevision = st.number_input("Previsión Social (Beneficios) ($)", min_value=0.0, value=3998.0, step=100.0)
    input_carga_social = st.number_input("Carga Social (IMSS, INFONAVIT, ISN) ($)", min_value=0.0, value=10511.0, step=500.0)

st.sidebar.header("📦 4. Opción Tercerizada")
tarifa_subcontratista = st.sidebar.number_input("Tarifa plana contratista (MXN)", min_value=0, value=38000, step=1000)
viaticos_foraneo_fijo = st.sidebar.number_input("Viáticos fijos (Si aplica personal foráneo) ($)", min_value=0, value=15000, step=500)

# --- LÓGICA MATEMÁTICA CENTRAL (RÍGIDA) ---
# Capacidad instalada en jornada regular
capacidad_normal_local = trabajadores_locales * dias_meta * jornada_diaria 
deficit_horas = max(0, horas_vendidas - capacidad_normal_local)

def calcular_matriz_costos(horas_evaluadas):
    """Calcula el desglose financiero exacto basado en las horas solicitadas"""
    # Los costos de nómina base actúan como un costo fijo del periodo contratado
    s_base = input_salario_base
    vars_cost = input_variables
    prov_ley = input_provisiones
    prev_soc = input_prevision
    c_social = input_carga_social
    
    t_extra = 0.0
    viaticos_foraneo = 0.0
    
    # Si el esfuerzo supera la jornada regular, se dispara el tiempo extra
    if horas_evaluadas > capacidad_normal_local:
        horas_extras_necesarias = horas_evaluadas - capacidad_normal_local
        
        # Costo de la hora base por trabajador
        if capacidad_normal_local > 0:
            costo_hora_regular = s_base / capacidad_normal_local
        else:
            costo_hora_regular = 0
            
        # Aplicación del factor de la Ley Federal del Trabajo (LFT)
        t_extra = horas_extras_necesarias * costo_hora_regular * factor_tiempo_extra
        viaticos_foraneo = viaticos_foraneo_fijo
        
    costo_interno = s_base + vars_cost + prov_ley + prev_soc + c_social + t_extra
    costo_foraneo = s_base + vars_cost + prov_ley + prev_soc + c_social + t_extra + viaticos_foraneo
    costo_subcontrata = tarifa_subcontratista
    
    return {
        "Salario Base": s_base,
        "Tiempo Extra": t_extra,
        "Variables": vars_cost,
        "Provisiones Ley": prov_ley,
        "Previsión Social": prev_soc,
        "Carga Social": c_social,
        "Viáticos": viaticos_foraneo if horas_evaluadas > capacidad_normal_local else 0.0,
        "Total Interna": costo_interno,
        "Total Foránea": costo_foraneo,
        "Total Subcontrata": costo_subcontrata
    }

# Obtener costos para el punto actual del proyecto
valores_actuales = calcular_matriz_costos(horas_vendidas)

# --- TARJETAS DE DIAGNÓSTICO SUPERIOR (KPIs) ---
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.metric(
        label="CAPACIDAD NORMAL LOCAL", 
        value=f"{capacidad_normal_local} hrs", 
        help=f"{trabajadores_locales} trabajadores x {dias_meta} días x {jornada_diaria} horas de jornada regular."
    )
with col_kpi2:
    obreros_equivalentes = horas_vendidas / (dias_meta * jornada_diaria) if (dias_meta * jornada_diaria) > 0 else 0
    st.metric(
        label="ESFUERZO SOLICITADO", 
        value=f"{horas_vendidas} hrs", 
        delta=f"Equivale a {obreros_equivalentes:.2f} obreros en jornada regular",
        delta_color="off"
    )
with col_kpi3:
    if deficit_horas == 0:
        st.metric(label="DÉFICIT A CUBRIR", value="0 hrs", delta="✅ Cubierto con jornada regular", delta_color="inverse")
    else:
        st.metric(label="DÉFICIT A CUBRIR", value=f"{deficit_horas} hrs", delta="⚠️ Requiere tiempo extra o apoyo foráneo", delta_color="normal")

st.markdown("---")

# --- DISTRIBUCIÓN VISUAL: TABLA DE COSTOS VS GRÁFICA DE SENSIBILIDAD ---
col_tabla, col_grafica = st.columns([1, 1.2])

with col_tabla:
    st.subheader("📋 Desglose de Costo Acumulado (TNG)")
    
    # Construcción estructurada del DataFrame
    df_comparativo = pd.DataFrame({
        "CATEGORÍA DE GASTO": [
            "🟢 Salario Base", 
            "🕒 Tiempo Extra (Variables LFT)", 
            "📈 Variables / Bonos", 
            "📝 Provisiones Ley (Finiquito)", 
            "🏥 Previsión Social Beneficios", 
            "🏢 Carga Social (IMSS/INFONAVIT)", 
            "✈️ Viáticos y Gastos Operativos", 
            "💰 TOTAL ACUMULADO"
        ],
        "OPC. 1 INTERNA": [
            valores_actuales["Salario Base"], valores_actuales["Tiempo Extra"], valores_actuales["Variables"],
            valores_actuales["Provisiones Ley"], valores_actuales["Previsión Social"], valores_actuales["Carga Social"],
            0.0, valores_actuales["Total Interna"]
        ],
        "OPC. 2 FORÁNEA": [
            valores_actuales["Salario Base"], valores_actuales["Tiempo Extra"], valores_actuales["Variables"],
            valores_actuales["Provisiones Ley"], valores_actuales["Previsión Social"], valores_actuales["Carga Social"],
            valores_actuales["Viáticos"], valores_actuales["Total Foránea"]
        ],
        "OPC. 3 SUBCONTRATA": [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 
            tarifa_subcontratista if horas_vendidas > 0 else 0.0, 
            tarifa_subcontratista
        ]
    })
    
    # Formateo dinámico a moneda nacional mexicana
    df_moneda = df_comparativo.copy()
    for col in ["OPC. 1 INTERNA", "OPC. 2 FORÁNEA", "OPC. 3 SUBCONTRATA"]:
        df_moneda[col] = df_moneda[col].map(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
        
    st.dataframe(df_moneda, hide_index=True, use_container_width=True)
    
    # Alertas de apoyo para la toma de decisiones rápidas
    opciones_costos = {
        "Interna": valores_actuales["Total Interna"],
        "Foránea": valores_actuales["Total Foránea"],
        "Subcontratación": tarifa_subcontratista
    }
    mejor_opcion = min(opciones_costos, key=opciones_costos.get)
    st.success(f"💡 **Recomendación Financiera:** La opción más eficiente para **{horas_vendidas} horas** es la **{mejor_opcion}** (Costo: ${opciones_costos[mejor_opcion]:,.2f}).")

with col_grafica:
    st.subheader("📈 Gráfica de Sensibilidad Financiera")
    
    # Generar rango dinámico para el eje X (horas del proyecto)
    rango_horas = np.arange(96, 481, 12)
    
    curva_interna = []
    curva_foranea = []
    curva_subcontrata = []
    
    for h in rango_horas:
        c = calcular_matriz_costos(h)
        curva_interna.append(c["Total Interna"])
        curva_foranea.append(c["Total Foránea"])
        curva_subcontrata.append(c["Total Subcontrata"])
        
    # Creación del gráfico interactivo con Plotly
    fig = go.Figure()
    
    # Líneas de tendencia
    fig.add_trace(go.Scatter(x=rango_horas, y=curva_interna, name="Opc 1: Interna", line=dict(color="#10b981", width=3)))
    fig.add_trace(go.Scatter(x=rango_horas, y=curva_foranea, name="Opc 2: Foránea", line=dict(color="#f59e0b", width=3)))
    fig.add_trace(go.Scatter(x=rango_horas, y=curva_subcontrata, name="Opc 3: Tercerizada", line=dict(color="#6366f1", width=3)))
    
    # Línea guía vertical de capacidad máxima local
    fig.add_vline(
        x=capacidad_normal_local, 
        line_width=2, 
        line_dash="dash", 
        line_color="#6b7280",
        annotation_text=f"Límite Capacidad ({capacidad_normal_local}h)", 
        annotation_position="top left"
    )
    
    # Punto marcador del estado actual seleccionado por el usuario
    fig.add_trace(go.Scatter(
        x=[horas_vendidas], 
        y=[valores_actuales["Total Interna"] if mejor_opcion != "Subcontratación" else tarifa_subcontratista], 
        mode="markers", 
        marker=dict(size=14, color="#ef4444", symbol="diamond"), 
        name="Proyecto Actual"
    ))
    
    fig.update_layout(
        xaxis_title="Esfuerzo Solicitado (Horas)",
        yaxis_title="Costo Acumulado Total ($ MXN)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
        plot_bgcolor="#fafafa"
    )
    
    st.plotly_chart(fig, use_container_width=True)