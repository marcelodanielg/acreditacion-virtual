import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# Configuración de la página con tema centrado y título
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# Archivos de datos
EXCEL_PADRON = "docentes.xlsx"
EXCEL_ASISTENCIA = "asistencia_registrada.xlsx"
ARCHIVO_LINK = "link_config.txt"

# --- MANEJO DEL LINK DINÁMICO ---
def leer_link_actual():
    if os.path.exists(ARCHIVO_LINK):
        with open(ARCHIVO_LINK, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "https://ingrese-el-link-desde-el-panel-de-control.com"

def guardar_nuevo_link(nuevo_url):
    url_limpia = nuevo_url.strip()
    if url_limpia and not (url_limpia.startswith("http://") or url_limpia.startswith("https://")):
        url_limpia = "https://" + url_limpia
        
    with open(ARCHIVO_LINK, "w", encoding="utf-8") as f:
        f.write(url_limpia)

# --- INICIALIZACIÓN DE ESTADOS ---
if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""

# Cargar Padrón
@st.cache_data(ttl=10)
def cargar_padron():
    if os.path.exists(EXCEL_PADRON):
        return pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
    else:
        return pd.DataFrame(columns=["dni", "apellido", "nombre"])

df_excel = cargar_padron()
df_total_habilitados = pd.concat([df_excel, st.session_state.nuevos_docentes], ignore_index=True)


# ==========================================
# PANEL DE ADMINISTRACIÓN (Barra Lateral)
# ==========================================
st.sidebar.markdown("## 🔐 Panel de Soporte")
password = st.sidebar.text_input("Contraseña de Acceso", type="password", help="Introduzca la clave de administrador")

if password == "admin123":
    st.sidebar.success("Acceso concedido")
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: ENLACE ---
    st.sidebar.subheader("🔗 Enlace de la Capacitación")
    link_actual = leer_link_actual()
    nuevo_link = st.sidebar.text_input("URL de Destino (Zoom/YT/Meet)", value=link_actual)
    
    if nuevo_link != link_actual:
        guardar_nuevo_link(nuevo_link)
        st.sidebar.success("¡Enlace actualizado!")
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: DESCARGAR Y REINICIAR ---
    st.sidebar.subheader("📥 Gestión de Asistencias")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
        
        # --- NUEVA MEJORA DE INTERFAZ: Métricas en vivo para el Admin ---
        st.sidebar.markdown("### 📊 Indicadores del Día")
        total_presentes = len(df_descarga)
        total_auto_registrados = len(st.session_state.nuevos_docentes)
        
        col_m1, col_m2 = st.sidebar.columns(2)
        col_m1.metric("Acreditados", total_presentes)
        col_m2.metric("Nuevos (Auto)", total_auto_registrados)
        st.sidebar.markdown("---")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_descarga.to_excel(writer, index=False, sheet_name='Presentes')
        
        st.sidebar.download_button(
            label="📊 Descargar Reporte (Excel)",
            data=buffer.getvalue(),
            file_name=f"asistencia_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.sidebar.markdown("---")
        st.sidebar.warning("⚠️ Zona de Peligro")
        confirmar_borrado = st.sidebar.checkbox("Confirmar eliminación permanente")
        btn_reiniciar = st.sidebar.button("♻️ Reiniciar Base de Asistencias", type="secondary", use_container_width=True)
        
        if btn_reiniciar:
            if confirmar_borrado:
                try:
                    os.remove(EXCEL_ASISTENCIA)
                    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])
                    st.sidebar.success("¡Base de datos limpia!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
            else:
                st.sidebar.error("❌ tilde la casilla para confirmar.")
    else:
        st.sidebar.info("Aún no se registran asistencias en esta sesión.")


# ==========================================
# INTERFAZ PÚBLICA DEL DOCENTE (Estilizada)
# ==========================================

# Encabezado estético superior
logo_col, title_col = st.columns([1, 5])
with logo_col:
    st.markdown("## 🎓")
with title_col:
    st.markdown("# Portal de Acreditación Virtual")

st.markdown("Estimado/a docente, ingrese su número de documento para registrar su asistencia y habilitar el botón de acceso a la sala virtual.")
st.markdown("---")

# Contenedor del formulario principal
with st.container(border=True):
    st.markdown("### 📝 Validar Identidad")
    with st.form("form_acreditacion", clear_on_submit=False):
        dni_ingresado = st.text_input("Número de DNI (sin puntos ni espacios)", max_chars=9, placeholder="Ej: 28444333")
        
        # Centramos visualmente el botón
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            boton_enviar = st.form_submit_button("Validar e Ingresar a la Sala", use_container_width=True)

# Procesamiento de la acreditación
if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingrese un número de DNI válido.")
    else:
        st.session_state.mostrar_autoregistro = False
        dni_ingresado = dni_ingresado.strip()
        link_destino = leer_link_actual()
        
        ya_presente = False
        datos_presente = None
        
        if os.path.exists(EXCEL_ASISTENCIA):
            df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
            coincidencia_asistencia = df_asistencias_viejas[df_asistencias_viejas['dni'] == dni_ingresado]
            if not coincidencia_asistencia.empty:
                ya_presente = True
                datos_presente = coincidencia_asistencia.iloc[0]

        # DISEÑO MEJORADO: Usamos cajas de estado estilizadas para las respuestas
        if ya_presente:
            with st.container(border=True):
                st.info(f"ℹ️ **Registro Previo Detectado:** Usted ya cuenta con asistencia asentada en este evento.")
                st.markdown(f"**Docente:** {datos_presente['apellido']}, {datos_presente['nombre']} | **DNI:** {dni_ingresado}")
                st.markdown("---")
                st.link_button("🚀 Volver a Ingresar a la Capacitación", link_destino, type="primary", use_container_width=True)
            
        else:
            coincidencia_padron = df_total_habilitados[df_total_habilitados['dni'] == dni_ingresado]
            
            if not coincidencia_padron.empty:
                apellido_real = coincidencia_padron.iloc[0]['apellido']
                nombre_real = coincidencia_padron.iloc[0]['nombre']
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                nueva_asistencia = pd.DataFrame([{
                    "dni": dni_ingresado, 
                    "nombre": nombre_real, 
                    "apellido": apellido_real, 
                    "fecha_hora": ahora
                }])
                
                if os.path.exists(EXCEL_ASISTENCIA):
                    df_final = pd.concat([df_asistencias_viejas, nueva_asistencia], ignore_index=True)
                else:
                    df_final = nueva_asistencia
                
                df_final.to_excel(EXCEL_ASISTENCIA, index=False)
                
                with st.container(border=True):
                    st.success(f"✅ **¡Acreditación Exitosa!** Sea bienvenido/a, **{nombre_real} {apellido_real}**.")
                    st.markdown("La asistencia se ha registrado de forma correcta en el sistema.")
                    st.markdown("---")
                    st.link_button("🚀 Acceder a la Sala Virtual", link_destino, type="primary", use_container_width=True)
            else:
                st.session_state.mostrar_autoregistro = True
                st.session_state.dni_pendiente = dni_ingresado


# ==========================================
# SECCIÓN CONDICIONAL: FORMULARIO DE AUTO-REGISTRO
# ==========================================
if st.session_state.mostrar_autoregistro:
    st.markdown("<br>", unsafe_allow_html=True) # Espaciador estético
    
    # Enmarcamos el auto-registro en una tarjeta clara
    with st.container(border=True):
        st.warning("⚠️ **DNI no encontrado en el padrón base.**")
        st.markdown("Si es docente de la institución o invitado/a, complete sus datos por única vez para darse de alta e ingresar de forma inmediata.")
        
        with st.form("form_autoregistro"):
            st.markdown(f"**Documento a registrar:** `{st.session_state.dni_pendiente}`")
            
            col1, col2 = st.columns(2)
            with col1:
                auto_apellido = st.text_input("Apellido Completo", placeholder="Ej: GOMEZ")
            with col2:
                auto_nombre = st.text_input("Nombres", placeholder="Ej: Juan Carlos")
                
            st.markdown("<br>", unsafe_allow_html=True)
            _, col_auto_btn, _ = st.columns([1, 2, 1])
            with col_auto_btn:
                boton_auto_guardar = st.form_submit_button("Confirmar Datos y Entrar", use_container_width=True)
        
        if boton_auto_guardar:
            if auto_apellido and auto_nombre:
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ape_formateado = auto_apellido.strip().upper()
                nom_formateado = auto_nombre.strip().title()
                
                link_destino = leer_link_actual()
                
                docente_nuevo = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente,
                    "apellido": ape_formateado,
                    "nombre": nom_formateado
                }])
                st.session_state.nuevos_docentes = pd.concat([st.session_state.nuevos_docentes, docente_nuevo], ignore_index=True)
                
                nueva_asistencia = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente, 
                    "nombre": nom_formateado, 
                    "apellido": ape_formateado, 
                    "fecha_hora": ahora
                }])
                
                if os.path.exists(EXCEL_ASISTENCIA):
                    df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                    df_final = pd.concat([df_asistencias_viejas, nueva_asistencia], ignore_index=True)
                else:
                    df_final = nueva_asistencia
                
                df_final.to_excel(EXCEL_ASISTENCIA, index=False)
                
                st.session_state.mostrar_autoregistro = False
                st.success(f"🎉 ¡Alta completada! Bienvenido/a, {nom_formateado}.")
                st.link_button("🚀 Entrar a la Capacitación", link_destino, type="primary", use_container_width=True)
                st.rerun()
            else:
                st.error("❌ Ambos campos son obligatorios para el alta.")
