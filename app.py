import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# Configuración de la página web
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# Nombres de los archivos de datos en el servidor
EXCEL_PADRON = "docentes.xlsx"
EXCEL_ASISTENCIA = "asistencia_registrada.xlsx"

# Link de la capacitación (Modificalo por tu enlace real de Zoom o YouTube)
LINK_CONFERENCIA = "https://zoom.us/j/tu_link_de_zoom"

# 1. FUNCIÓN PARA CARGAR EL PADRÓN DESDE EXCEL
@st.cache_data(ttl=60)
def cargar_padron():
    if os.path.exists(EXCEL_PADRON):
        # Lee el archivo asegurando que el DNI se procese como texto
        return pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
    else:
        # Padrón vacío de respaldo si el archivo no se encuentra
        return pd.DataFrame(columns=["dni", "apellido", "nombre"])

df_excel = cargar_padron()

# 2. MANEJO DE NUEVOS ACCESOS MANUALES (En la sesión activa)
if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

# Combinamos el Excel base con las altas dadas por soporte en vivo
df_total_habilitados = pd.concat([df_excel, st.session_state.nuevos_docentes], ignore_index=True)


# ==========================================
# PANEL DE ADMINISTRACIÓN (Barra Lateral)
# ==========================================
st.sidebar.title("🔐 Panel de Soporte")
password = st.sidebar.text_input("Contraseña de Admin", type="password")

# Cambiá "admin123" por la contraseña maestra que desees
if password == "admin123":
    st.sidebar.success("Acceso concedido")
    
    # --- SECCIÓN: DESCARGAR REPORTE DE PRESENTES ---
    st.sidebar.subheader("📥 Descargar Reporte")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA)
        
        # Preparación del archivo en memoria para la descarga
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_descarga.to_excel(writer, index=False, sheet_name='Presentes')
        
        st.sidebar.download_button(
            label="📊 Descargar Excel de Asistencia",
            data=buffer.getvalue(),
            file_name=f"asistencia_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.sidebar.warning("Aún no hay asistencias registradas.")
        
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: ALTA MANUAL EN CALIENTE ---
    st.sidebar.subheader("Registrar Nuevo Docente Manualmente")
    with st.sidebar.form("alta_manual", clear_on_submit=True):
        nuevo_dni = st.text_input("DNI (sin puntos)")
        nuevo_ape = st.text_input("Apellido")
        nuevo_nom = st.text_input("Nombre")
        btn_guardar = st.form_submit_button("Habilitar Acceso")
        
        if btn_guardar:
            if nuevo_dni and nuevo_ape and nuevo_nom:
                nueva_fila = pd.DataFrame([{
                    "dni": nuevo_dni.strip(), 
                    "apellido": nuevo_ape.strip(), 
                    "nombre": nuevo_nom.strip()
                }])
                st.session_state.nuevos_docentes = pd.concat([st.session_state.nuevos_docentes, nueva_fila], ignore_index=True)
                st.sidebar.success(f"🎓 Habilitado: {nuevo_ape}, {nuevo_nom}")
                st.rerun()
            else:
                st.sidebar.error("Completá todos los campos")


# ==========================================
# INTERFAZ PÚBLICA DEL DOCENTE
# ==========================================
st.title("🎓 Sistema de Acreditación Virtual")
st.write("Ingresá tus datos para validar tu asistencia y recibir el enlace de acceso.")

with st.form("form_acreditacion"):
    dni_ingresado = st.text_input("Número de DNI (sin puntos)", max_chars=9)
    apellido_ingresado = st.text_input("Primer Apellido")
    boton_enviar = st.form_submit_button("Validar e Ingresar")

if boton_enviar:
    if not dni_ingresado or not apellido_ingresado:
        st.error("⚠️ Por favor, completá ambos campos.")
    else:
        dni_ingresado = dni_ingresado.strip()
        apellido_ingresado = apellido_ingresado.strip().lower()
        
        # Validación contra el padrón unificado
        coincidencia = df_total_habilitados[df_total_habilitados['dni'] == dni_ingresado]
        
        if not coincidencia.empty:
            apellido_real = str(coincidencia.iloc[0]['apellido']).lower()
            nombre_real = coincidencia.iloc[0]['nombre']
            
            if apellido_ingresado in apellido_real:
                # --- REGISTRO DE ASISTENCIA EN EL SERVIDOR ---
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                nueva_asistencia = pd.DataFrame([{
                    "dni": dni_ingresado, 
                    "nombre": nombre_real, 
                    "apellido": coincidencia.iloc[0]['apellido'], 
                    "fecha_hora": ahora
                }])
                
                if os.path.exists(EXCEL_ASISTENCIA):
                    df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                    df_final = pd.concat([df_asistencias_viejas, nueva_asistencia], ignore_index=True)
                else:
                    df_final = nueva_asistencia
                
                # Evita duplicar filas si el mismo docente toca el botón varias veces
                df_final.drop_duplicates(subset=["dni"], keep="first", inplace=True)
                df_final.to_excel(EXCEL_ASISTENCIA, index=False)
                
                # --- DESPLIEGUE DEL ACCESO SEGURO ---
                st.success(f"✅ ¡Validación exitosa! Bienvenido/a, {nombre_real}.")
                st.markdown("### 📝 Asistencia asentada correctamente")
                st.write("Hacé clic abajo para ingresar a la sala de la capacitación:")
                st.link_button("🚀 Entrar a la Capacitación", LINK_CONFERENCIA, type="primary", use_container_width=True)
            else:
                st.error("❌ El apellido no coincide con el DNI ingresado.")
        else:
            st.error("❌ El DNI no se encuentra en el padrón. Si te inscribiste recientemente, comunicate con el equipo de soporte.")
