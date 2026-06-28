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

# --- INICIALIZACIÓN DE ESTADOS ---
if "link_conferencia" not in st.session_state:
    st.session_state.link_conferencia = "https://us05web.zoom.us/j/82339060910?pwd=OFUzcg6wXPcSwPhwEl8fxdwa06yfYf.1"

if "nuevos_docentes" not in st.session_state:
    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])

if "mostrar_autoregistro" not in st.session_state:
    st.session_state.mostrar_autoregistro = False
if "dni_pendiente" not in st.session_state:
    st.session_state.dni_pendiente = ""


# 1. FUNCIÓN PARA CARGAR EL PADRÓN DESDE EXCEL
@st.cache_data(ttl=60)
def cargar_padron():
    if os.path.exists(EXCEL_PADRON):
        return pd.read_excel(EXCEL_PADRON, dtype={"dni": str})
    else:
        return pd.DataFrame(columns=["dni", "apellido", "nombre"])

df_excel = cargar_padron()

# Combinamos el Excel base con las altas dadas por soporte o auto-registro en vivo
df_total_habilitados = pd.concat([df_excel, st.session_state.nuevos_docentes], ignore_index=True)


# ==========================================
# PANEL DE ADMINISTRACIÓN (Barra Lateral)
# ==========================================
st.sidebar.title("🔐 Panel de Soporte")
password = st.sidebar.text_input("Contraseña de Admin", type="password")

if password == "admin123":
    st.sidebar.success("Acceso concedido")
    
    # --- SECCIÓN: CONFIGURACIÓN DEL ENLACE EN VIVO ---
    st.sidebar.subheader("🔗 Configuración del Enlace")
    nuevo_link = st.sidebar.text_input("Enlace de la Capacitación (Zoom/YT)", value=st.session_state.link_conferencia)
    if nuevo_link != st.session_state.link_conferencia:
        st.session_state.link_conferencia = nuevo_link
        st.sidebar.info("¡Enlace actualizado para los docentes!")
    
    st.sidebar.markdown("---")
    
    # --- SECCIÓN: DESCARGAR REPORTE DE PRESENTES ---
    st.sidebar.subheader("📥 Descargar Reporte")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
        
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
                    "apellido": nuevo_ape.strip().upper(), 
                    "nombre": nuevo_nom.strip().title()
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
st.write("Ingresá tu número de documento para validar tu asistencia y recibir el enlace de acceso.")

# Formulario simplificado: Solo pide el DNI
with st.form("form_acreditacion"):
    dni_ingresado = st.text_input("Número de DNI (sin puntos)", max_chars=9)
    boton_enviar = st.form_submit_button("Validar e Ingresar")

# Procesamiento de la acreditación
if boton_enviar:
    if not dni_ingresado:
        st.error("⚠️ Por favor, ingresá tu número de DNI.")
    else:
        st.session_state.mostrar_autoregistro = False
        dni_ingresado = dni_ingresado.strip()
        
        # 1. CONTROL DE DUPLICADOS: Verificar si ya registró asistencia previa
        ya_presente = False
        datos_presente = None
        
        if os.path.exists(EXCEL_ASISTENCIA):
            df_asistencias_viejas = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
            coincidencia_asistencia = df_asistencias_viejas[df_asistencias_viejas['dni'] == dni_ingresado]
            if not coincidencia_asistencia.empty:
                ya_presente = True
                datos_presente = coincidencia_asistencia.iloc[0]

        if ya_presente:
            # Si ya se encuentra registrado, no duplica y da paso directo mostrando sus datos
            st.info(f"ℹ️ Ya registraste tu asistencia anteriormente.")
            st.markdown(f"**Datos registrados:** DNI: {dni_ingresado} | Docente: {datos_presente['apellido']}, {datos_presente['nombre']}")
            st.link_button("🚀 Volver a entrar a la Capacitación", st.session_state.link_conferencia, type="primary", use_container_width=True)
            
        else:
            # 2. VALIDACIÓN CONTRA EL PADRÓN (Si no tiene asistencia previa)
            coincidencia_padron = df_total_habilitados[df_total_habilitados['dni'] == dni_ingresado]
            
            if not coincidencia_padron.empty:
                apellido_real = coincidencia_padron.iloc[0]['apellido']
                nombre_real = coincidencia_padron.iloc[0]['nombre']
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Guardar nueva asistencia
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
                
                st.success(f"✅ ¡Validación exitosa! Bienvenido/a, {nombre_real} {apellido_real}.")
                st.markdown("### 📝 Asistencia asentada correctamente")
                st.link_button("🚀 Entrar a la Capacitación", st.session_state.link_conferencia, type="primary", use_container_width=True)
            else:
                # Si el DNI no está en el padrón ni en asistencias, abre el auto-registro
                st.session_state.mostrar_autoregistro = True
                st.session_state.dni_pendiente = dni_ingresado


# ==========================================
# SECCIÓN CONDICIONAL: AUTO-REGISTRO
# ==========================================
if st.session_state.mostrar_autoregistro:
    st.warning("⚠️ Tu DNI no figura en el padrón institucional. Completá tus datos abajo para registrarte y acceder.")
    
    with st.form("form_autoregistro"):
        st.write(f"**DNI a registrar:** {st.session_state.dni_pendiente}")
        auto_apellido = st.text_input("Apellido Completo")
        auto_nombre = st.text_input("Nombres")
        boton_auto_guardar = st.form_submit_button("Confirmar Asistencia e Ingresar")
        
        if boton_auto_guardar:
            if auto_apellido and auto_nombre:
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ape_formateado = auto_apellido.strip().upper()
                nom_formateado = auto_nombre.strip().title()
                
                # Añadir a la sesión para que el padrón lo reconozca si actualiza la página
                docente_nuevo = pd.DataFrame([{
                    "dni": st.session_state.dni_pendiente,
                    "apellido": ape_formateado,
                    "nombre": nom_formateado
                }])
                st.session_state.nuevos_docentes = pd.concat([st.session_state.nuevos_docentes, docente_nuevo], ignore_index=True)
                
                # Escribir en el archivo de asistencias directamente
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
                
                # Ocultar formulario de registro y dar la bienvenida
                st.session_state.mostrar_autoregistro = False
                st.success(f"🎉 ¡Registro exitoso! Bienvenido/a, {nom_formateado}.")
                st.link_button("🚀 Entrar a la Capacitación", st.session_state.link_conferencia, type="primary", use_container_width=True)
            else:
                st.error("❌ Por favor, rellene ambos campos para poder proceder.")
