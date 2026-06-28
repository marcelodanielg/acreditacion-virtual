import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import qrcode
from streamlit_gsheets import GSheetsConnection

# Configuración de la página con tema centrado y estética compacta
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# Ocultamos de raíz TODOS los elementos flotantes de Streamlit y Streamlit Cloud (iconos, coronas, menús, etc.)
st.markdown("""
    <style>
        /* Reducir márgenes superiores */
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        
        /* Ocultar interfaces nativas de Streamlit */
        footer {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        #MainMenu {visibility: hidden; display: none !important;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}
        
        /* Ocultar los botones flotantes de administración de Streamlit Cloud (esquina inferior derecha) */
        iframe[title="Streamlit Cloud Toolbar"] {display: none !important; visibility: hidden !important;}
        div[class*="viewerBadge"] {display: none !important; visibility: hidden !important;}
        button[class*="StyledAppActionButton"] {display: none !important; visibility: hidden !important;}
        div[data-testid="stDecoration"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- LOGO DEL MINISTERIO DE EDUCACIÓN DE SAN JUAN ---
URL_LOGO_MINISTERIO = "https://educacion.sanjuan.gob.ar/mesj/LinkClick.aspx?fileticket=w376Zbe_pXo%3d&portalid=4&language=es-AR"

st.image(URL_LOGO_MINISTERIO, use_container_width=True)
st.markdown("---")

# Archivos locales secundarios
EXCEL_PADRON = "docentes.xlsx"
ARCHIVO_LINK = "link_config.txt"

# --- CONEXIÓN DIRECTA CON GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def leer_asistencias_sheets():
    try:
        # Lee la pestaña principal de la hoja configurada en los secrets
        return conn.read(ttl=0) # ttl=0 obliga a buscar datos frescos de Google siempre
    except Exception:
        # Si está vacía o da error inicial, retorna la estructura limpia
        return pd.DataFrame(columns=["dni", "nombre", "apellido", "fecha_hora_entrada", "fecha_hora_salida", "minutos_conectado"])

def guardar_asistencias_sheets(df_a_guardar):
    # Asegura tipos string para evitar problemas de formato científico con los DNI
    df_a_guardar["dni"] = df_a_guardar["dni"].astype(str)
    conn.update(data=df_a_guardar)

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

# --- DETECTAR MODO (ENTRADA O SALIDA) ---
query_params = st.query_params
es_modo_salida = query_params.get("accion") == "salida"

# --- INICIALIZACIÓN DE ESTADOS INTERNOS ---
if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""
if "estado_flujo" not in st.session_state:
    st.session_state.estado_flujo = "formulario"
if "datos_docente_actual" not in st.session_state:
    st.session_state.datos_docente_actual = {}

# FUNCIÓN PARA CARGAR EL PADRÓN BASE LOCAL
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
password = st.sidebar.text_input("Contraseña de Acceso", type="password")

if password == "admin123":
    st.sidebar.success("Acceso concedido")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("🔗 Enlace de la Sala")
    link_actual = leer_link_actual()
    nuevo_link = st.sidebar.text_input("URL de Destino", value=link_actual)
    
    if nuevo_link != link_actual:
        guardar_nuevo_link(nuevo_link)
        st.sidebar.success("¡Enlace actualizado!")
        st.rerun()
    
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("🖼️ QR de Acreditación de Salida")
    url_salida = "https://acreditacionvirtual.streamlit.app/?accion=salida"
        
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url_salida)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    buf_qr = io.BytesIO()
    img_qr.save(buf_qr, format="PNG")
    byte_im_qr = buf_qr.getvalue()
    
    st.sidebar.image(byte_im_qr, caption="Escanear para registrar Egreso", width=150)
    
    st.sidebar.download_button(
        label="📥 Descargar Imagen QR",
        data=byte_im_qr,
        file_name="qr_salida_capacitacion.png",
        mime="image/png",
        use_container_width=True
    )
    
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("📥 Gestión de Planilla Cloud")
    df_descarga = leer_asistencias_sheets()
    
    # Limpiamos filas completamente vacías que Sheets suele retornar
    df_descarga = df_descarga.dropna(how='all')
    
    total_historico = len(df_descarga)
    con_salida = df_descarga["fecha_hora_salida"].notna().sum() if "fecha_hora_salida" in df_descarga.columns else 0
    
    st.sidebar.markdown("### 📊 Indicadores en Google Sheets")
    col_m1, col_m2 = st.sidebar.columns(2)
    col_m1.metric("Total Ingresos", total_historico)
    col_m2.metric("Total Egresos", con_salida)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_descarga.to_excel(writer, index=False, sheet_name='Historial_GoogleSheets')
    
    st.sidebar.download_button(
        label="📊 Descargar Respaldo Local (Excel)",
        data=buffer.getvalue(),
        file_name=f"asistencias_sheets_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )


# ==========================================
# PANTALLAS DE ÉXITO
# ==========================================
if st.session_state.estado_flujo == "exito_entrada":
    link_destino = leer_link_actual()
    with st.container(border=True):
        st.success(f"✅ **¡Acreditación Guardada Impecable!**")
        st.markdown(f"### Bienvenido/a, **{st.session_state.datos_docente_actual.get('nombre')} {st.session_state.datos_docente_actual.get('apellido')}**")
        st.markdown("Presioná el siguiente botón para abrir la sala de la videoconferencia:")
        
        st.link_button("🚀 INGRESAR A LA CAPACITACIÓN", link_destino, type="primary", use_container_width=True)
    st.stop()

elif st.session_state.estado_flujo == "exito_salida":
    with st.container(border=True):
        st.success(f"📥 **¡Egreso Asentado con Éxito!**")
        st.markdown(f"### Muchas gracias por participar, **{st.session_state.datos_docente_actual.get('nombre')}**.")
        st.markdown(f"⏱️ **Tiempo final de permanencia:** {st.session_state.datos_docente_actual.get('minutos')} minutos.")
        
        st.info("🔒 **Tu asistencia de cierre ha sido procesada de forma segura.** Ya podés cerrar o salir de este sitio en tu navegador.")
    st.stop()


# ==========================================
# INTERFAZ PÚBLICA DEL DOCENTE (FORMULARIO BASE)
# ==========================================
if es_modo_salida:
    st.markdown("## 🎓 Registro de Salida")
    st.markdown("Ingrese su DNI para **asentar su egreso** y calcular el tiempo total de permanencia.")
else:
    st.markdown("## 🎓 Portal de Acreditación Virtual")
    st.markdown("Ingrese su número de documento para validar su asistencia y habilitar el ingreso.")

with st.container(border=True):
    with st.form("form_acreditacion", clear_on_submit=False):
        dni_ingresado = st.text_input("Número de DNI (sin puntos ni espacios)", max_chars=9, placeholder="Ej: 28444333")
        
        _, col_btn, _ = st.columns([0.5, 2, 0.5])
        with col_btn:
            texto_boton = "Confirmar Egreso 📤" if es_modo_salida else "Validar e Ingresar a la Sala 🚀"
            boton_enviar = st.form_submit_button(texto_boton, use_container_width=True)

if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingrese un número de DNI válido.")
    else:
        dni_ingresado = dni_ingresado.strip()
        ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ahora_dt = datetime.now()
        
        # Traemos la base completa y fresca de Google Sheets
        df_asistencias = leer_asistencias_sheets()
        df_asistencias = df_asistencias.dropna(how='all')
        df_asistencias["dni"] = df_asistencias["dni"].astype(str).str.split('.').str[0].str.strip()

        # -----------------------------------------------------------------
        # [MODO SALIDA]: Lógica de Egreso usando Google Sheets
        # -----------------------------------------------------------------
        if es_modo_salida:
            idx = df_asistencias[(df_asistencias['dni'] == dni_ingresado) & (df_asistencias['fecha_hora_salida'].isna() | (df_asistencias['fecha_hora_salida'] == ""))].index
            
            if not idx.empty:
                fila_objetivo = idx[-1]
                entrada_str = df_asistencias.loc[fila_objetivo, "fecha_hora_entrada"]
                
                if pd.isna(entrada_str) or entrada_str == "":
                    entrada_dt = ahora_dt
                    df_asistencias.at[fila_objetivo, "fecha_hora_entrada"] = ahora_str
                else:
                    entrada_dt = datetime.strptime(str(entrada_str), "%Y-%m-%d %H:%M:%S")
                
                diferencia = ahora_dt - entrada_dt
                minutos_totales = round(diferencia.total_seconds() / 60, 1)
                
                df_asistencias.at[fila_objetivo, "fecha_hora_salida"] = ahora_str
                df_asistencias.at[fila_objetivo, "minutos_conectado"] = minutos_totales
                
                # Guardamos la actualización en la nube
                guardar_asistencias_sheets(df_asistencias)
                
                st.session_state.datos_docente_actual = {
                    "nombre": df_asistencias.loc[fila_objetivo, 'nombre'],
                    "minutos": minutos_totales
                }
                st.session_state.estado_flujo = "exito_salida"
                st.rerun()
            else:
                idx_historico = df_asistencias[df_asistencias['dni'] == dni_ingresado].index
                if not idx_historico.empty:
                    fila_h = idx_historico[-1]
                    st.session_state.datos_docente_actual = {
                        "nombre": df_asistencias.loc[fila_h, 'nombre'],
                        "minutos": df_asistencias.loc[fila_h, 'minutos_conectado'] if not pd.isna(df_asistencias.loc[fila_h, 'minutos_conectado']) else 0
                    }
                    st.session_state.estado_flujo = "exito_salida"
                    st.rerun()
                else:
                    st.error("❌ No se encontró ningún registro de 'Entrada' en la planilla de Google Sheets para este DNI.")

        # -----------------------------------------------------------------
        # [MODO ENTRADA]: Lógica de Ingreso usando Google Sheets
        # -----------------------------------------------------------------
        else:
            st.session_state.mostrar_autoregistro = False
            coincidencia_padron = df_total_habilitados[df_total_habilitados['dni'] == dni_ingresado]
            
            if not coincidencia_padron.empty:
                apellido_real = coincidencia_padron.iloc[0]['apellido']
                nombre_real = coincidencia_padron.iloc[0]['nombre']
                
                nueva_asistencia = pd.DataFrame([{
                    "dni": dni_ingresado, 
                    "nombre": nombre_real, 
                    "apellido": apellido_real, 
                    "fecha_hora_entrada": ahora_str,
                    "fecha_hora_salida": "",
                    "minutos_conectado": ""
                }])
                
                df_final = pd.concat([df_asistencias, nueva_asistencia], ignore_index=True)
                guardar_asistencias_sheets(df_final)
                
                st.session_state.datos_docente_actual = {
                    "nombre": nombre_real,
                    "apellido": apellido_real
                }
                st.session_state.estado_flujo = "exito_entrada"
                st.rerun()
            else:
                st.session_state.mostrar_autoregistro = True
                st.session_state.dni_pendiente = dni_ingresado


# ==========================================
# SECCIÓN CONDICIONAL: FORMULARIO DE AUTO-REGISTRO
# ==========================================
if st.session_state.mostrar_autoregistro and not es_modo_salida:
    with st.container(border=True):
        st.warning("⚠️ **DNI no encontrado.** Complete sus datos por única vez para darse de alta.")
        with st.form("form_autoregistro"):
            st.markdown(f"**Documento:** `{st.session_state.dni_pendiente}`")
            col1, col2 = st.columns(2)
            with col1:
                auto_apellido = st.text_input("Apellido/s", placeholder="Ej: GOMEZ")
            with col2:
                auto_nombre = st.text_input("Nombre/s", placeholder="Ej: Juan Carlos")
                
            _, col_auto_btn, _ = st.columns([0.5, 2, 0.5])
            with col_auto_btn:
                boton_auto_guardar = st.form_submit_button("Confirmar Registro y Entrar", use_container_width=True)
        
        if boton_auto_guardar:
            if auto_apellido and auto_nombre:
                ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ape_formateado = auto_apellido.strip().upper()
                nom_formateado = auto_nombre.strip().title()
                
                docente_nuevo = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente,
                    "apellido": ape_formateado,
                    "nombre": nom_formateado
                }])
                st.session_state.nuevos_docentes = pd.concat([st.session_state.nuevos_docentes, docente_nuevo], ignore_index=True)
                
                df_asistencias = leer_asistencias_sheets()
                df_asistencias = df_asistencias.dropna(how='all')
                
                nueva_asistencia = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente, 
                    "nombre": nom_formateado, 
                    "apellido": ape_formateado, 
                    "fecha_hora_entrada": ahora_str,
                    "fecha_hora_salida": "",
                    "minutos_conectado": ""
                }])
                
                df_final = pd.concat([df_asistencias, nueva_asistencia], ignore_index=True)
                guardar_asistencias_sheets(df_final)
                
                st.session_state.mostrar_autoregistro = False
                st.session_state.datos_docente_actual = {
                    "nombre": nom_formateado,
                    "apellido": ape_formateado
                }
                st.session_state.estado_flujo = "exito_entrada"
                st.rerun()
            else:
                st.error("❌ Ambos campos son obligatorios.")
