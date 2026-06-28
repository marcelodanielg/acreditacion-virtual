import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# Configuración de la página con tema centrado y estética limpia
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# Nombres de los archivos de datos en el servidor
EXCEL_PADRON = "docentes.xlsx"
EXCEL_ASISTENCIA = "asistencia_registrada.xlsx"
ARCHIVO_LINK = "link_config.txt"

# --- MANEJO DEL LINK DINÁMICO CON VALIDACIÓN HTTP ---
def leer_link_actual():
    if os.path.exists(ARCHIVO_LINK):
        with open(ARCHIVO_LINK, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "https://ingrese-el-link-desde-el-panel-de-control.com"

def guardar_nuevo_link(nuevo_url):
    url_limpia = nuevo_url.strip()
    # Si el administrador ingresa un link sin protocolo (ej: www.diariodecuyo.com.ar), se le auto-agrega https://
    if url_limpia and not (url_limpia.startswith("http://") or url_limpia.startswith("https://")):
        url_limpia = "https://" + url_limpia
    with open(ARCHIVO_LINK, "w", encoding="utf-8") as f:
        f.write(url_limpia)

# --- DETECTAR MODO (ENTRADA O SALIDA) DESDE LA URL ---
# El QR de salida debe apuntar a: tu-app.streamlit.app/?accion=salida
query_params = st.query_params
es_modo_salida = query_params.get("accion") == "salida"

# --- INICIALIZACIÓN DE ESTADOS INTERNOS ---
if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""

# 1. FUNCIÓN PARA CARGAR EL PADRÓN BASE
@st.cache_data(ttl=10)
def cargar_padron():
    if os.path.exists(EXCEL_PADRON):
        return pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
    else:
        return pd.DataFrame(columns=["dni", "apellido", "nombre"])

df_excel = cargar_padron()

# Padrón total unificado (base + auto-registrados en la sesión)
df_total_habilitados = pd.concat([df_excel, st.session_state.nuevos_docentes], ignore_index=True)


# ==========================================
# PANEL DE ADMINISTRACIÓN (Barra Lateral)
# ==========================================
st.sidebar.markdown("## 🔐 Panel de Soporte")
password = st.sidebar.text_input("Contraseña de Acceso", type="password", help="Introduzca la clave de administrador")

if password == "admin123":
    st.sidebar.success("Acceso concedido")
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: CONFIGURACIÓN DEL ENLACE EN VIVO ---
    st.sidebar.subheader("🔗 Enlace de la Capacitación")
    link_actual = leer_link_actual()
    nuevo_link = st.sidebar.text_input("URL de Destino (Zoom/YT/Meet)", value=link_actual)
    
    if nuevo_link != link_actual:
        guardar_nuevo_link(nuevo_link)
        st.sidebar.success("¡Enlace actualizado!")
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: DESCARGAR Y REINICIAR REPORTE DE PRESENTES ---
    st.sidebar.subheader("📥 Gestión de Asistencias")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
        
        # Indicadores estadísticos en tiempo real para el administrador
        total_presentes = len(df_descarga)
        con_salida = df_descarga["fecha_hora_salida"].notna().sum() if "fecha_hora_salida" in df_descarga.columns else 0
        
        st.sidebar.markdown("### 📊 Indicadores del Día")
        col_m1, col_m2 = st.sidebar.columns(2)
        col_m1.metric("Ingresos", total_presentes)
        col_m2.metric("Egresos (QR)", con_salida)
        st.sidebar.markdown("---")
        
        # Preparación de descarga en memoria sin corromper el Excel activo
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
        
        # Reinicio Seguro de la Base de datos
        st.sidebar.warning("⚠️ Zona de Peligro")
        confirmar_borrado = st.sidebar.checkbox("Confirmar eliminación permanente")
        btn_reiniciar = st.sidebar.button("♻️ Reiniciar Base de Asistencias", type="secondary", use_container_width=True)
        
        if btn_reiniciar:
            if confirmar_borrado:
                try:
                    os.remove(EXCEL_ASISTENCIA)
                    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])
                    st.sidebar.success("¡Base de datos limpia para una nueva jornada!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error al vaciar registros: {e}")
            else:
                st.sidebar.error("❌ Tilde la casilla de confirmación primero.")
    else:
        st.sidebar.info("Aún no se registran asistencias en el día.")


# ==========================================
# INTERFAZ PÚBLICA DEL DOCENTE (ESTILIZADA)
# ==========================================
logo_col, title_col = st.columns([1, 5])
with logo_col:
    st.markdown("## 🎓")
with title_col:
    if es_modo_salida:
        st.markdown("# Registro de Salida de Capacitación")
    else:
        st.markdown("# Portal de Acreditación Virtual")

if es_modo_salida:
    st.markdown("Estimado/a docente, ingrese su documento para **asentar su egreso** y computar el tiempo total de permanencia.")
else:
    st.markdown("Estimado/a docente, ingrese su número de documento para registrar su asistencia y habilitar el acceso a la sala virtual.")
st.markdown("---")

# Contenedor del formulario principal
with st.container(border=True):
    if es_modo_salida:
        st.markdown("### 📤 Registrar Salida")
    else:
        st.markdown("### 📝 Validar Identidad (Ingreso)")
        
    with st.form("form_acreditacion", clear_on_submit=False):
        dni_ingresado = st.text_input("Número de DNI (sin puntos ni espacios)", max_chars=9, placeholder="Ej: 28444333")
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            texto_boton = "Confirmar Egreso" if es_modo_salida else "Validar e Ingresar a la Sala"
            boton_enviar = st.form_submit_button(texto_boton, use_container_width=True)

# Procesamiento de la información
if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingrese un número de DNI válido.")
    else:
        dni_ingresado = dni_ingresado.strip()
        ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ahora_dt = datetime.now()
        
        # -----------------------------------------------------------------
        # [MODO SALIDA]: Activado cuando escanean el QR (?accion=salida)
        # -----------------------------------------------------------------
        if es_modo_salida:
            if os.path.exists(EXCEL_ASISTENCIA):
                df_asistencias = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                idx = df_asistencias[df_asistencias['dni'] == dni_ingresado].index
                
                if not idx.empty:
                    # Si no ha marcado la salida previa, calculamos el tiempo conectado
                    if pd.isna(df_asistencias.loc[idx[0], "fecha_hora_salida"]):
                        entrada_str = df_asistencias.loc[idx[0], "fecha_hora_entrada"]
                        entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Cálculo matemático de permanencia exacta
                        diferencia = ahora_dt - entrada_dt
                        minutos_totales = round(diferencia.total_seconds() / 60, 1)
                        
                        df_asistencias.loc[idx[0], "fecha_hora_salida"] = ahora_str
                        df_asistencias.loc[idx[0], "minutos_conectado"] = minutos_totales
                        df_asistencias.to_excel(EXCEL_ASISTENCIA, index=False)
                        
                        with st.container(border=True):
                            st.success(f"🎉 **¡Salida Registrada!** Muchas gracias por su asistencia, **{df_asistencias.loc[idx[0], 'nombre']}**.")
                            st.markdown(f"⏱️ **Tiempo total computado:** {minutos_totales} minutos.")
                    else:
                        with st.container(border=True):
                            st.info("ℹ️ Su egreso ya fue registrado anteriormente en esta jornada.")
                            st.markdown(f"**Tiempo total asentado:** {df_asistencias.loc[idx[0], 'minutos_conectado']} minutos.")
                else:
                    st.error("❌ No se encontró registro de 'Entrada' para este DNI. Asegúrese de haber validado su ingreso al inicio.")
            else:
                st.error("❌ Todavía no hay ninguna asistencia registrada en el sistema el día de hoy.")

        # -----------------------------------------------------------------
        # [MODO ENTRADA]: Flujo normal de acreditación
        # -----------------------------------------------------------------
        else:
            st.session_state.mostrar_autoregistro = False
            link_destino = leer_link_actual()
            
            ya_presente = False
            datos_presente = None
            
            if os.path.exists(EXCEL_ASISTENCIA):
                df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                # Compatibilidad si el archivo venía de una estructura antigua
                if "fecha_hora_entrada" not in df_asistencias_viejas.columns:
                    df_asistencias_viejas.rename(columns={"fecha_hora": "fecha_hora_entrada"}, inplace=True)
                
                coincidencia_asistencia = df_asistencias_viejas[df_asistencias_viejas['dni'] == dni_ingresado]
                if not coincidencia_asistencia.empty:
                    ya_presente = True
                    datos_presente = coincidencia_asistencia.iloc[0]

            if ya_presente:
                with st.container(border=True):
                    st.info(f"ℹ️ **Asistencia de Entrada Ya Registrada:** Usted ya se acreditó previamente.")
                    st.markdown(f"**Docente:** {datos_presente['apellido']}, {datos_presente['nombre']} | **DNI:** {dni_ingresado}")
                    st.markdown("---")
                    st.link_button("🚀 Volver a Entrar a la Sala Virtual", link_destino, type="primary", use_container_width=True)
            else:
                coincidencia_padron = df_total_habilitados
