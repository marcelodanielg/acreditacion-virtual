import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
import qrcode
from PIL import Image

# Configuración de la página con tema centrado y estética compacta
st.set_page_config(page_title="Acreditación Virtual", page_icon="🎓", layout="centered")

# Reducimos los márgenes superiores nativos de Streamlit para evitar el scroll vertical
st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Nombres de los archivos de datos
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
    if url_limpia and not (url_limpia.startswith("http://") or url_limpia.startswith("https://")):
        url_limpia = "https://" + url_limpia
    with open(ARCHIVO_LINK, "w", encoding="utf-8") as f:
        f.write(url_limpia)

# --- DETECTAR MODO (ENTRADA O SALIDA) DESDE LA URL ---
query_params = st.query_params
es_modo_salida = query_params.get("accion") == "salida"

# --- INICIALIZACIÓN DE ESTADOS INTERNOS ---
if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""

# FUNCIÓN PARA CARGAR EL PADRÓN BASE
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
    
    # Enlace de la capacitación
    st.sidebar.subheader("🔗 Enlace de la Sala")
    link_actual = leer_link_actual()
    nuevo_link = st.sidebar.text_input("URL de Destino", value=link_actual)
    
    if nuevo_link != link_actual:
        guardar_nuevo_link(nuevo_link)
        st.sidebar.success("¡Enlace actualizado!")
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # --- NUEVA MEJORA: GENERACIÓN Y DESCARGA AUTOMÁTICA DEL QR DE SALIDA ---
    st.sidebar.subheader("🖼️ QR de Acreditación de Salida")
    
    # Construcción dinámica de la URL de salida basándose en el dominio actual de la app
    try:
        url_base_app = st.get_option("browser.gatherUsageStats") # Intento de fallback seguro
        # Alternativa estándar construida dinámicamente si estás en Streamlit Cloud
        url_salida = "https://acreditacionvirtual.streamlit.app/?accion=salida"
    except:
        url_salida = "https://acreditacionvirtual.streamlit.app/?accion=salida"
        
    # Crear código QR en memoria
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url_salida)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar la imagen en un buffer de bytes para que Streamlit pueda ofrecer su descarga
    buf_qr = io.BytesIO()
    img_qr.save(buf_qr, format="PNG")
    byte_im_qr = buf_qr.getvalue()
    
    # Mostrar vista previa pequeña en el panel de soporte
    st.sidebar.image(byte_im_qr, caption="Escanear para registrar Egreso", width=150)
    
    # Botón de descarga directa del QR
    st.sidebar.download_button(
        label="📥 Descargar Imagen QR",
        data=byte_im_qr,
        file_name="qr_salida_capacitacion.png",
        mime="image/png",
        use_container_width=True
    )
    
    st.sidebar.markdown("---")
    
    # Gestión de descargas del Excel y reinicio
    st.sidebar.subheader("📥 Gestión de Asistencias")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
        
        total_presentes = len(df_descarga)
        con_salida = df_descarga["fecha_hora_salida"].notna().sum() if "fecha_hora_salida" in df_descarga.columns else 0
        
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
            file_name=f"asistencia_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.sidebar.markdown("---")
        st.sidebar.warning("⚠️ Zona de Peligro")
        confirmar_borrado = st.sidebar.checkbox("Confirmar eliminación permanente")
        btn_reiniciar = st.sidebar.button("♻️ Reiniciar Base de Asistencias", type="secondary", use_container_width=True)
        
        if btn_reiniciar and confirmar_borrado:
            try:
                os.remove(EXCEL_ASISTENCIA)
                st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])
                st.sidebar.success("¡Base de datos limpia!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
    else:
        st.sidebar.info("Aún no se registran asistencias.")


# ==========================================
# INTERFAZ PÚBLICA DEL DOCENTE (DISEÑO ULTRA COMPACTO)
# ==========================================
# Usamos un formato en una sola línea para ahorrar espacio vertical crítico
if es_modo_salida:
    st.markdown("## 🎓 Registro de Salida")
    st.markdown("Ingrese su DNI para **asentar su egreso** y calcular el tiempo total de permanencia.")
else:
    st.markdown("## 🎓 Portal de Acreditación Virtual")
    st.markdown("Ingrese su número de documento para validar su asistencia y habilitar el ingreso.")

# Contenedor del formulario principal (Ajustado para evitar barras de desplazamiento)
with st.container(border=True):
    with st.form("form_acreditacion", clear_on_submit=False):
        dni_ingresado = st.text_input("Número de DNI (sin puntos ni espacios)", max_chars=9, placeholder="Ej: 28444333")
        
        _, col_btn, _ = st.columns([0.5, 2, 0.5])
        with col_btn:
            texto_boton = "Confirmar Egreso 📤" if es_modo_salida else "Validar e Ingresar a la Sala 🚀"
            boton_enviar = st.form_submit_button(texto_boton, use_container_width=True)

# Procesamiento de la información
if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingrese un número de DNI válido.")
    else:
        dni_ingresado = dni_ingresado.strip()
        ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ahora_dt = datetime.now()
        
        # [MODO SALIDA]: Activado por el QR con ?accion=salida
        if es_modo_salida:
            if os.path.exists(EXCEL_ASISTENCIA):
                df_asistencias = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                idx = df_asistencias[df_asistencias['dni'] == dni_ingresado].index
                
                if not idx.empty:
                    if pd.isna(df_asistencias.loc[idx[0], "fecha_hora_salida"]):
                        entrada_str = df_asistencias.loc[idx[0], "fecha_hora_entrada"]
                        entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
                        
                        diferencia = ahora_dt - entrada_dt
                        minutos_totales = round(diferencia.total_seconds() / 60, 1)
                        
                        df_asistencias.loc[idx[0], "fecha_hora_salida"] = ahora_str
                        df_asistencias.loc[idx[0], "minutos_conectado"] = minutos_totales
                        df_asistencias.to_excel(EXCEL_ASISTENCIA, index=False)
                        
                        with st.container(border=True):
                            st.success(f"🎉 ¡Salida Registrada!, **{df_asistencias.loc[idx[0], 'nombre']}**.")
                            st.markdown(f"⏱️ **Tiempo total conectado:** {minutos_totales} minutos.")
                    else:
                        with st.container(border=True):
                            st.info("ℹ️ Su egreso ya fue registrado anteriormente en esta jornada.")
                            st.markdown(f"**Tiempo total asentado:** {df_asistencias.loc[idx[0], 'minutos_conectado']} minutos.")
                else:
                    st.error("❌ No se encontró registro de 'Entrada' para este DNI.")
            else:
                st.error("❌ Todavía no hay ninguna asistencia registrada el día de hoy.")

        # [MODO ENTRADA]: Flujo normal de acreditación
        else:
            st.session_state.mostrar_autoregistro = False
            link_destino = leer_link_actual()
            
            ya_presente = False
            datos_presente = None
            
            if os.path.exists(EXCEL_ASISTENCIA):
                df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                if "fecha_hora_entrada" not in df_asistencias_viejas.columns:
                    df_asistencias_viejas.rename(columns={"fecha_hora": "fecha_hora_entrada"}, inplace=True)
                
                coincidencia_asistencia = df_asistencias_viejas[df_asistencias_viejas['dni'] == dni_ingresado]
                if not coincidencia_asistencia.empty:
                    ya_presente = True
                    datos_presente = coincidencia_asistencia.iloc[0]

            if ya_presente:
                with st.container(border=True):
                    st.info(f"ℹ️ **Ingreso ya registrado:**")
                    st.markdown(f"**Docente:** {datos_presente['apellido']}, {datos_presente['nombre']}")
                    st.link_button("🚀 Volver a Entrar a la Sala Virtual", link_destino, type="primary", use_container_width=True)
            else:
                coincidencia_padron = df_total_habilitados[df_total_habilitados['dni'] == dni_ingresado]
                
                if not coincidencia_padron.empty:
                    apellido_real = coincidencia_padron.iloc[0]['apellido']
                    nombre_real = coincidencia_padron.iloc[0]['nombre']
                    
                    nueva_asistencia = pd.DataFrame([{
                        "dni": dni_ingresado, 
                        "nombre": nombre_real, 
                        "apellido": apellido_real, 
                        "fecha_hora_entrada": ahora_str,
                        "fecha_hora_salida": None,
                        "minutos_conectado": None
                    }])
                    
                    if os.path.exists(EXCEL_ASISTENCIA):
                        df_final = pd.concat([df_asistencias_viejas, nueva_asistencia], ignore_index=True)
                    else:
                        df_final = nueva_asistencia
                    
                    df_final.to_excel(EXCEL_ASISTENCIA, index=False)
                    
                    with st.container(border=True):
                        st.success(f"✅ **Acreditación Exitosa:** ¡Bienvenido/a, **{nombre_real} {apellido_real}**!")
                        st.link_button("🚀 Acceder a la Sala Virtual", link_destino, type="primary", use_container_width=True)
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
                    "fecha_hora_entrada": ahora_str,
                    "fecha_hora_salida": None,
                    "minutos_conectado": None
                }])
                
                if os.path.exists(EXCEL_ASISTENCIA):
                    df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
                    df_final = pd.concat([df_asistencias_viejas, nueva_asistencia], ignore_index=True)
                else:
                    df_final = nueva_asistencia
                
                df_final.to_excel(EXCEL_ASISTENCIA, index=False)
                
                st.session_state.mostrar_autoregistro = False
                st.success(f"🎉 ¡Alta exitosa! Bienvenido/a.")
                st.link_button("🚀 Entrar a la Capacitación", link_destino, type="primary", use_container_width=True)
                st.rerun()
            else:
                st.error("❌ Ambos campos son obligatorios.")
