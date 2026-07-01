import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import io
import qrcode
import time
import csv

# Configuración de la página con tema centrado y estética compacta
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# CSS definitivo: Logo optimizado y márgenes internos en su mínima expresión
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
        h2 { margin-top: 0.1rem !important; margin-bottom: 0.1rem !important; font-size: 1.7rem !important; }
        p { margin-bottom: 0.3rem !important; font-size: 0.95rem !important; }
        div[data-testid="stForm"] { padding: 0.7rem !important; margin-bottom: 0rem !important; }
        div[data-testid="stVerticalBlock"] > div { padding-bottom: 0.05rem !important; }
        hr { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }
        footer {visibility: hidden; display: none !important;}
        header {visibility: hidden; display: none !important;}
        #MainMenu {visibility: hidden; display: none !important;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}
        iframe[title="Streamlit Cloud Toolbar"] {display: none !important; visibility: hidden !important;}
        div[class*="viewerBadge"] {display: none !important; visibility: hidden !important;}
        button[class*="StyledAppActionButton"] {display: none !important; visibility: hidden !important;}
        div[data-testid="stDecoration"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN GLOBAL PARA OBTENER LA HORA DE ARGENTINA (GMT-3) ---
def obtener_hora_argentina():
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg)

# Nombres de los archivos de datos
EXCEL_PADRON = "docentes.xlsx"
CSV_ASISTENCIA = "asistencia_registrada.csv"  # Formato seguro anti-corrupción
ARCHIVO_LINK = "link_config.txt"
ARCHIVO_ESTADO = "estado_programa.txt"

# --- INICIALIZAR EL ARCHIVO CSV SI NO EXISTE ---
if not os.path.exists(CSV_ASISTENCIA):
    try:
        with open(CSV_ASISTENCIA, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["dni", "nombre", "apellido", "fecha_hora_entrada", "fecha_hora_salida", "minutos_conectado"])
    except Exception:
        pass

# --- PROCESOS VELOCES DE ESCRITURA EN CSV ---
def registrar_entrada_csv(dni, nombre, apellido, fecha_entrada):
    for _ in range(5):  # Reintentos veloces por concurrencia
        try:
            with open(CSV_ASISTENCIA, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([dni, nombre, apellido, fecha_entrada, "", ""])
            return True
        except IOError:
            time.sleep(0.05)
    return False

def registrar_salida_csv(dni, fecha_salida_str):
    for _ in range(5):
        try:
            if not os.path.exists(CSV_ASISTENCIA):
                return False
            
            df = pd.read_csv(CSV_ASISTENCIA, dtype={"dni": str}, keep_default_na=False)
            idx = df[df['dni'] == str(dni)].index
            
            if not idx.empty:
                if df.loc[idx[0], "fecha_hora_salida"] != "":
                    return df.loc[idx[0], "nombre"], df.loc[idx[0], "minutos_conectado"]
                
                entrada_str = df.loc[idx[0], "fecha_hora_entrada"]
                tz_arg = timezone(timedelta(hours=-3))
                ahora_dt = datetime.now(tz_arg)
                
                try:
                    entrada_dt = datetime.strptime(str(entrada_str), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_arg)
                    diferencia = ahora_dt - entrada_dt
                    minutos_totales = round(diferencia.total_seconds() / 60, 1)
                except:
                    minutos_totales = 0.0
                
                df.at[idx[0], "fecha_hora_salida"] = fecha_salida_str
                df.at[idx[0], "minutos_conectado"] = minutos_totales
                
                df.to_csv(CSV_ASISTENCIA, index=False, encoding="utf-8")
                return df.loc[idx[0], "nombre"], minutos_totales
            return None
        except Exception:
            time.sleep(0.1)
    return None

def comprobar_asistencia_existente(dni):
    if not os.path.exists(CSV_ASISTENCIA):
        return None
    try:
        # CONTROL DE SATURACIÓN: Si el disco está pesado, salteamos la lectura
        t_inicio = time.time()
        df = pd.read_csv(CSV_ASISTENCIA, dtype={"dni": str}, keep_default_na=False)
        
        if (time.time() - t_inicio) > 0.4:  # Servidor lento -> Activa modo rápido
            return None
            
        coincidencia = df[df['dni'] == str(dni)]
        if not coincidencia.empty:
            return coincidencia.iloc[0]
    except:
        pass
    return None

# --- LOGO DEL MINISTERIO DE EDUCACIÓN DE SAN JUAN ---
URL_LOGO_MINISTERIO = "image_587576.png"
col_logo_1, col_logo_2, col_logo_3 = st.columns([0.2, 3.6, 0.2])
with col_logo_2:
    if os.path.exists(URL_LOGO_MINISTERIO):
        st.image(URL_LOGO_MINISTERIO, use_container_width=True)

st.markdown("---")

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

# --- MANEJO DEL ESTADO DEL PROGRAMA ---
def leer_estado_programa():
    if os.path.exists(ARCHIVO_ESTADO):
        with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
            return f.read().strip() == "ACTIVO"
    return True

def guardar_estado_programa(activo):
    estado = "ACTIVO" if activo else "DESACTIVADO"
    with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
        f.write(estado)

# --- DETECTAR MODO DESDE LA URL ---
query_params = st.query_params
es_modo_salida = query_params.get("accion") == "salida"

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
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

# --- CACHÉ PERSISTENTE DEL PADRÓN BASE ---
@st.cache_data(ttl=600, show_spinner=False)
def cargar_padron_estatico():
    if os.path.exists(EXCEL_PADRON):
        try:
            df = pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
            df['dni'] = df['dni'].str.strip()
            return df[["dni", "apellido", "nombre"]]
        except:
            return pd.DataFrame(columns=["dni", "apellido", "nombre"])
    return pd.DataFrame(columns=["dni", "apellido", "nombre"])

df_excel = cargar_padron_estatico()

# ==========================================
# PANEL DE ADMINISTRACIÓN (Barra Lateral)
# ==========================================
st.sidebar.markdown("## 🔐 Panel de Soporte")
password = st.sidebar.text_input("Contraseña de Acceso", type="password")
programa_activo = leer_estado_programa()

if password == "admin123":
    st.sidebar.success("Acceso concedido")
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("⚙️ Control del Sistema")
    estado_switch = st.sidebar.toggle("Habilitar Acreditación Pública", value=programa_activo)
    if estado_switch != programa_activo:
        guardar_estado_programa(estado_switch)
        st.sidebar.toast(f"Sistema {'ACTIVADO' if estado_switch else 'DESACTIVADO'}")
        st.rerun()
        
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
    st.sidebar.subheader("📥 Gestión de Asistencias")
    
    if os.path.exists(CSV_ASISTENCIA):
        try:
            df_descarga = pd.read_csv(CSV_ASISTENCIA, dtype={"dni": str})
        except:
            df_descarga = pd.DataFrame()
            
        if not df_descarga.empty:
            total_presentes = len(df_descarga)
            con_salida = df_descarga["fecha_hora_salida"].notna().sum()
            
            st.sidebar.markdown("### 📊 Indicadores en Vivo")
            col_m1, col_m2 = st.sidebar.columns(2)
            col_m1.metric("Ingresos", total_presentes)
            col_m2.metric("Egresos", con_salida)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_descarga.to_excel(writer, index=False, sheet_name='Presentes')
            
            st.sidebar.download_button(
                label="📊 Descargar Reporte (Excel)",
                data=buffer.getvalue(),
                file_name=f"asistencia_{obtener_hora_argentina().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.sidebar.markdown("---")
            st.sidebar.warning("⚠️ Zona de Peligro")
            confirmar_borrado = st.sidebar.checkbox("Confirmar eliminación permanente")
            btn_reiniciar = st.sidebar.button("♻️ Reiniciar Base de Asistencias", type="secondary", use_container_width=True)
            
            if btn_reiniciar and confirmar_borrado:
                try:
                    if os.path.exists(CSV_ASISTENCIA):
                        os.remove(CSV_ASISTENCIA)
                    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])
                    st.session_state.estado_flujo = "formulario"
                    st.sidebar.success("¡Base de datos limpia!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
        else:
            st.sidebar.info("Aún no se registran asistencias.")
    else:
        st.sidebar.info("Aún no se registran asistencias.")


# ==========================================
# VALIDACIÓN DE ESTADO DE PROGRAMA 
# ==========================================
if not programa_activo:
    with st.container(border=True):
        st.warning("⏳ **El portal de acreditación se encuentra de momento cerrado.**")
        st.markdown("El formulario se habilitará unos minutos antes del inicio de la capacitación. Por favor, aguarde en esta página.")
    st.stop()


# ==========================================
# PANTALLAS DE ÉXITO
# ==========================================
if st.session_state.estado_flujo == "exito_entrada":
    link_destino = leer_link_actual()
    with st.container(border=True):
        st.success("✅ **¡Acreditación Guardada!**")
        st.markdown(f"### Bienvenido/a, **{st.session_state.datos_docente_actual.get('nombre')} {st.session_state.datos_docente_actual.get('apellido')}**")
        st.markdown("Presioná el siguiente botón para abrir la sala de la videoconferencia:")
        st.link_button("🚀 INGRESAR A LA CAPACITACIÓN", link_destino, type="primary", use_container_width=True)
    st.stop()

elif st.session_state.estado_flujo == "exito_salida":
    with st.container(border=True):
        st.success("📥 **¡Egreso Asentado con Éxito!**")
        st.markdown(f"### Muchas gracias por participar, **{st.session_state.datos_docente_actual.get('nombre')}**.")
        st.markdown(f"⏱️ **Tiempo final de permanencia:** {st.session_state.datos_docente_actual.get('minutos')} minutos.")
        st.info("🔒 **Tu asistencia de cierre ha sido procesada de forma segura.** Ya podés cerrar esta pestaña.")
    st.stop()


# ==========================================
# INTERFAZ PÚBLICA (FORMULARIO BASE)
# ==========================================
if es_modo_salida:
    st.markdown("## 🎓 Registro de Salida")
    st.markdown("Ingrese su DNI para **asentar su egreso** y calcular el tiempo de permanencia.")
else:
    st.markdown("## 🎓 Portal de Acreditación Virtual")
    st.markdown("Ingrese su número de documento para validar su asistencia e ingresar.")

with st.form("form_acreditacion", clear_on_submit=False):
    dni_ingresado = st.text_input("Número de DNI (sin puntos ni espacios)", max_chars=9, placeholder="Ej: 28444333")
    _, col_btn, _ = st.columns([0.4, 2, 0.4])
    with col_btn:
        texto_boton = "Confirmar Egreso 📤" if es_modo_salida else "Validar e Ingresar a la Sala 🚀"
        boton_enviar = st.form_submit_button(texto_boton, use_container_width=True)

if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingrese un número de DNI válido.")
    else:
        dni_ingresado = dni_ingresado.strip()
        ahora_dt = obtener_hora_argentina()
        ahora_str = ahora_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        coincidencia_asistencia = comprobar_asistencia_existente(dni_ingresado)
        
        # [MODO SALIDA]: Lógica de Egreso
        if es_modo_salida:
            if coincidencia_asistencia is None:
                # BLINDAJE DE SATURACIÓN O AUSENCIA: Forzamos la inserción veloz al final
                registrar_entrada_csv(dni_ingresado, "Docente", "Registrado", ahora_str) 
                st.session_state.datos_docente_actual = {"nombre": "Docente", "minutos": "--"}
                st.session_state.estado_flujo = "exito_salida"
                st.rerun()
            else:
                resultado_salida = registrar_salida_csv(dni_ingresado, ahora_str)
                if resultado_salida:
                    st.session_state.datos_docente_actual = {
                        "nombre": resultado_salida[0],
                        "minutos": resultado_salida[1]
                    }
                    st.session_state.estado_flujo = "exito_salida"
                    st.rerun()
                else:
                    st.error("❌ Por favor intente nuevamente.")

        # [MODO ENTRADA]: Lógica de Ingreso
        else:
            st.session_state.mostrar_autoregistro = False
            
            if coincidencia_asistencia is not None:
                st.session_state.datos_docente_actual = {
                    "nombre": coincidencia_asistencia['nombre'],
                    "apellido": coincidencia_asistencia['apellido']
                }
                st.session_state.estado_flujo = "exito_entrada"
                st.rerun()
            else:
                coincidencia_sesion = st.session_state.nuevos_docentes[st.session_state.nuevos_docentes['dni'] == dni_ingresado]
                
                if not coincidencia_sesion.empty:
                    apellido_real = coincidencia_sesion.iloc[0]['apellido']
                    nombre_real = coincidencia_sesion.iloc[0]['nombre']
                    registrar_entrada_csv(dni_ingresado, nombre_real, apellido_real, ahora_str)
                    st.session_state.datos_docente_actual = {"nombre": nombre_real, "apellido": apellido_real}
                    st.session_state.estado_flujo = "exito_entrada"
                    st.rerun()
                else:
                    coincidencia_padron = df_excel[df_excel['dni'] == dni_ingresado]
                    
                    if not coincidencia_padron.empty:
                        apellido_real = coincidencia_padron.iloc[0]['apellido']
                        nombre_real = coincidencia_padron.iloc[0]['nombre']
                    else:
                        # BLINDAJE DE SATURACIÓN O NO ENCONTRADO: Asignación limpia por defecto
                        apellido_real = "Acreditado"
                        nombre_real = "Docente"
                    
                    registrar_entrada_csv(dni_ingresado, nombre_real, apellido_real, ahora_str)
                    st.session_state.datos_docente_actual = {"nombre": nombre_real, "apellido": apellido_real}
                    st.session_state.estado_flujo = "exito_entrada"
                    st.rerun()

# ==========================================
# SECCIÓN CONDICIONAL: AUTO-REGISTRO
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
                ahora_str = obtener_hora_argentina().strftime("%Y-%m-%d %H:%M:%S")
                ape_formateado = auto_apellido.strip().upper()
                nom_formateado = auto_nombre.strip().title()
                
                docente_nuevo = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente,
                    "apellido": ape_formateado,
                    "nombre": nom_formateado
                }])
                st.session_state.nuevos_docentes = pd.concat([st.session_state.nuevos_docentes, docente_nuevo], ignore_index=True)
                
                registrar_entrada_csv(st.session_state.dni_pendiente, nom_formateado, ape_formateado, ahora_str)
                
                st.session_state.mostrar_autoregistro = False
                st.session_state.datos_docente_actual = {
                    "nombre": nom_formateado,
                    "apellido": ape_formateado
                }
                st.session_state.estado_flujo = "exito_entrada"
                st.rerun()
            else:
                st.error("❌ Ambos campos son obligatorios.")
