import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import io
import qrcode
import time
import csv
from filelock import FileLock

# Configuración de la página con tema centrado y estética compacta
st.set_page_config(
    page_title="Acreditación Virtual",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS definitivo: Ajustes de márgenes y visibilidad permitiendo despliegue del Sidebar
st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
        h2 { margin-top: 0.1rem !important; margin-bottom: 0.1rem !important; font-size: 1.7rem !important; }
        p { margin-bottom: 0.3rem !important; font-size: 0.95rem !important; }
        div[data-testid="stForm"] { padding: 0.7rem !important; margin-bottom: 0rem !important; }
        div[data-testid="stVerticalBlock"] > div { padding-bottom: 0.05rem !important; }
        hr { margin-top: 0.3rem !important; margin-bottom: 0.3rem !important; }
        footer {visibility: hidden; display: none !important;}
        #MainMenu {visibility: hidden; display: none !important;}
        .stAppDeployButton {display:none !important;}
        [data-testid="stStatusWidget"] {display:none !important;}
        iframe[title="Streamlit Cloud Toolbar"] {display: none !important; visibility: hidden !important;}
        div[class*="viewerBadge"] {display: none !important; visibility: hidden !important;}
        div[data-testid="stDecoration"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIÓN GLOBAL PARA OBTENER LA HORA DE ARGENTINA (GMT-3) ---
def obtener_hora_argentina():
    tz_arg = timezone(timedelta(hours=-3))
    return datetime.now(tz_arg)

# Nombres de los archivos de datos
EXCEL_PADRON = "docentes.xlsx"
CSV_ASISTENCIA = "asistencia_registrada.csv"  
LOCK_ASISTENCIA = "asistencia_registrada.csv.lock"
ARCHIVO_LINK = "link_config.txt"
ARCHIVO_ESTADO = "estado_programa.txt"

# --- INICIALIZAR EL ARCHIVO CSV SI NO EXISTE CON CONTROL DE CONCURRENCIA ---
if not os.path.exists(CSV_ASISTENCIA):
    lock = FileLock(LOCK_ASISTENCIA, timeout=5)
    try:
        with lock:
            if not os.path.exists(CSV_ASISTENCIA):
                with open(CSV_ASISTENCIA, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["dni", "nombre", "apellido", "tipo_registro", "fecha_hora"])
    except Exception:
        pass

# --- PROCESOS ULTRA VELOCES DE ESCRITURA EN CSV CON FILELOCK (CONCURRENCIA ALTÍSIMA) ---
def registrar_evento_csv(dni, nombre, apellido, tipo):
    ahora_str = obtener_hora_argentina().strftime("%Y-%m-%d %H:%M:%S")
    lock = FileLock(LOCK_ASISTENCIA, timeout=10)
    try:
        with lock:
            with open(CSV_ASISTENCIA, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([dni, nombre, apellido, tipo, ahora_str])
        return True
    except Exception:
        return False

# --- CACHÉ PERSISTENTE DEL PADRÓN BASE CON OPTIMIZACIÓN DE BÚSQUEDA ---
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_padron_diccionario():
    if os.path.exists(EXCEL_PADRON):
        try:
            df = pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
            df['dni'] = df['dni'].astype(str).str.strip()
            # Retorna un diccionario {dni: (nombre, apellido)} para búsqueda en tiempo constante O(1)
            padron_dict = {}
            for _, row in df.iterrows():
                padron_dict[row['dni']] = (str(row.get('nombre', '')), str(row.get('apellido', '')))
            return padron_dict
        except Exception:
            return {}
    return {}

padron_dict = cargar_padron_diccionario()

# Buscador rápido en el padrón o en asistencias previas
def buscar_nombre_en_padron_o_asistencia(dni):
    dni_str = str(dni).strip()
    
    # 1. Búsqueda en caché O(1)
    if dni_str in padron_dict:
        nom, ape = padron_dict[dni_str]
        return nom, ape
    
    # 2. Búsqueda en asistencias grabadas
    if os.path.exists(CSV_ASISTENCIA):
        lock = FileLock(LOCK_ASISTENCIA, timeout=5)
        try:
            with lock:
                df = pd.read_csv(CSV_ASISTENCIA, dtype={"dni": str}, keep_default_na=False)
            df['dni'] = df['dni'].astype(str).str.strip()
            coincidencia = df[df['dni'] == dni_str]
            if not coincidencia.empty:
                return coincidencia.iloc[0]['nombre'], coincidencia.iloc[0]['apellido']
        except Exception:
            pass
            
    return None, None

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
        try:
            with open(ARCHIVO_LINK, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return "https://ingrese-el-link-desde-el-panel-de-control.com"

def guardar_nuevo_link(nuevo_url):
    url_limpia = nuevo_url.strip()
    if url_limpia and not (url_limpia.startswith("http://") or url_limpia.startswith("https://")):
        url_limpia = "https://" + url_limpia
    try:
        with open(ARCHIVO_LINK, "w", encoding="utf-8") as f:
            f.write(url_limpia)
    except Exception:
        pass

# --- MANEJO DEL ESTADO DEL PROGRAMA ---
def leer_estado_programa():
    if os.path.exists(ARCHIVO_ESTADO):
        try:
            with open(ARCHIVO_ESTADO, "r", encoding="utf-8") as f:
                return f.read().strip() == "ACTIVO"
        except Exception:
            pass
    return True

def guardar_estado_programa(activo):
    estado = "ACTIVO" if activo else "DESACTIVADO"
    try:
        with open(ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
            f.write(estado)
    except Exception:
        pass

# --- DETECTAR MODO DESDE LA URL ---
query_params = st.query_params
es_modo_salida = query_params.get("accion") == "salida"

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""
if "estado_flujo" not in st.session_state:
    st.session_state.estado_flujo = "formulario"
if "datos_docente_actual" not in st.session_state:
    st.session_state.datos_docente_actual = {}

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
            lock = FileLock(LOCK_ASISTENCIA, timeout=5)
            with lock:
                df_crudo = pd.read_csv(CSV_ASISTENCIA, dtype={"dni": str})
        except Exception:
            df_crudo = pd.DataFrame()
            
        if not df_crudo.empty:
            ingresos_unicos = df_crudo[df_crudo["tipo_registro"] == "ENTRADA"]["dni"].nunique()
            egresos_unicos = df_crudo[df_crudo["tipo_registro"] == "SALIDA"]["dni"].nunique()
            
            st.sidebar.markdown("### 📊 Indicadores en Vivo")
            col_m1, col_m2 = st.sidebar.columns(2)
            col_m1.metric("Ingresos Reales", ingresos_unicos)
            col_m2.metric("Egresos Reales", egresos_unicos)
            
            # PROCESAMIENTO BAJO DEMANDA PARA EL REPORTE EXCEL FINAL
            df_entradas = df_crudo[df_crudo["tipo_registro"] == "ENTRADA"].drop_duplicates(subset=["dni"], keep="first")
            df_salidas = df_crudo[df_crudo["tipo_registro"] == "SALIDA"].drop_duplicates(subset=["dni"], keep="last")
            
            df_reporte = pd.merge(df_entradas[["dni", "nombre", "apellido", "fecha_hora"]], 
                                  df_salidas[["dni", "fecha_hora"]], 
                                  on="dni", how="left", suffixes=("_entrada", "_salida"))
            
            def calcular_minutos_reporte(row):
                if pd.isna(row["fecha_hora_salida"]) or pd.isna(row["fecha_hora_entrada"]):
                    return ""
                try:
                    e = datetime.strptime(str(row["fecha_hora_entrada"]), "%Y-%m-%d %H:%M:%S")
                    s = datetime.strptime(str(row["fecha_hora_salida"]), "%Y-%m-%d %H:%M:%S")
                    return round((s - e).total_seconds() / 60, 1)
                except Exception:
                    return ""
            
            if not df_reporte.empty:
                df_reporte["minutos_conectado"] = df_reporte.apply(calcular_minutos_reporte, axis=1)
            else:
                df_reporte["minutos_conectado"] = ""
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_reporte.to_excel(writer, index=False, sheet_name='Asistencia Procesada')
            
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
                    lock = FileLock(LOCK_ASISTENCIA, timeout=5)
                    with lock:
                        if os.path.exists(CSV_ASISTENCIA):
                            os.remove(CSV_ASISTENCIA)
                        with open(CSV_ASISTENCIA, mode="w", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow(["dni", "nombre", "apellido", "tipo_registro", "fecha_hora"])
                    st.session_state.estado_flujo = "formulario"
                    st.session_state.mostrar_autoregistro = False
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
        st.info("🔒 **Tu asistencia de cierre ha sido procesada de forma segura.** Ya podés cerrar esta pestaña.")
    st.stop()


# ==========================================
# INTERFAZ PÚBLICA (FORMULARIO BASE O AUTO-REGISTRO)
# ==========================================
if st.session_state.mostrar_autoregistro and not es_modo_salida:
    # FORMULARIO DE ALTA PARA DOCENTES NO ENCONTRADOS
    with st.container(border=True):
        st.warning("⚠️ **DNI no encontrado en el padrón.**")
        st.markdown("Por favor, ingrese sus datos por única vez para darse de alta en el sistema e ingresar:")
        
        with st.form("form_autoregistro"):
            st.markdown(f"**Documento:** `{st.session_state.dni_pendiente}`")
            col1, col2 = st.columns(2)
            with col1:
                auto_apellido = st.text_input("Apellido/s", placeholder="Ej: GOMEZ").strip().upper()
            with col2:
                auto_nombre = st.text_input("Nombre/s", placeholder="Ej: JUAN CARLOS").strip().title()
                
            _, col_auto_btn, _ = st.columns([0.5, 2, 0.5])
            with col_auto_btn:
                boton_auto_guardar = st.form_submit_button("Confirmar Datos y Entrar 🚀", use_container_width=True)
        
        if boton_auto_guardar:
            if auto_apellido and auto_nombre:
                registrar_evento_csv(st.session_state.dni_pendiente, auto_nombre, auto_apellido, "ENTRADA")
                st.session_state.datos_docente_actual = {"nombre": auto_nombre, "apellido": auto_apellido}
                st.session_state.mostrar_autoregistro = False
                st.session_state.estado_flujo = "exito_entrada"
                st.rerun()
            else:
                st.error("❌ Ambos campos son obligatorios.")
else:
    # FORMULARIO ESTÁNDAR DE INGRESO / EGRESO
    if es_modo_salida:
        st.markdown("## 🎓 Registro de Salida")
        st.markdown("Ingrese su DNI para **asentar su egreso** de la capacitación.")
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
            
            # Intentar recuperar nombre y apellido si ya existe o está en el padrón
            nom_detectado, ape_detectado = buscar_nombre_en_padron_o_asistencia(dni_ingresado)
            
            # [MODO SALIDA]: Lógica de Egreso Directo
            if es_modo_salida:
                nombre_final = nom_detectado if nom_detectado else "Docente"
                apellido_final = ape_detectado if ape_detectado else "Acreditado"
                registrar_evento_csv(dni_ingresado, nombre_final, apellido_final, "SALIDA")
                st.session_state.datos_docente_actual = {"nombre": nombre_final}
                st.session_state.estado_flujo = "exito_salida"
                st.rerun()

            # [MODO ENTRADA]: Lógica de Ingreso con Validación Real
            else:
                if nom_detectado is not None:
                    # Si ya estaba en el padrón o se auto-registró antes, pasa directo
                    registrar_evento_csv(dni_ingresado, nom_detectado, ape_detectado, "ENTRADA")
                    st.session_state.datos_docente_actual = {"nombre": nom_detectado, "apellido": ape_detectado}
                    st.session_state.estado_flujo = "exito_entrada"
                    st.rerun()
                else:
                    # NO ESTÁ: Saltamos al modo auto-registro reteniendo el DNI ingresado
                    st.session_state.dni_pendiente = dni_ingresado
                    st.session_state.mostrar_autoregistro = True
                    st.rerun()
