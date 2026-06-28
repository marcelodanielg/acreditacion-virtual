# --- SECCIÓN: DESCARGAR Y REINICIAR REPORTE DE PRESENTES ---
    st.sidebar.subheader("📥 Gestión de Asistencias")
    if os.path.exists(EXCEL_ASISTENCIA):
        df_descarga = pd.read_excel(EXCEL_ASISTENCIA, dtype={"dni": str})
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_descarga.to_excel(writer, index=False, sheet_name='Presentes')
        
        # Botón de descarga existente
        st.sidebar.download_button(
            label="📊 Descargar Excel de Asistencia",
            data=buffer.getvalue(),
            file_name=f"asistencia_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.sidebar.markdown("---")
        
        # Nueva funcionalidad de reinicio seguro
        st.sidebar.warning("⚠️ Zona de Peligro")
        confirmar_borrado = st.sidebar.checkbox("Confirmar eliminación permanente")
        btn_reiniciar = st.sidebar.button("♻️ Reiniciar Base de Asistencias", type="secondary", use_container_width=True)
        
        if btn_reiniciar:
            if confirmar_borrado:
                try:
                    # Eliminamos el archivo físico
                    os.remove(EXCEL_ASISTENCIA)
                    # Limpiamos los docentes auto-registrados en la sesión activa
                    st.session_state.nuevos_docentes = pd.DataFrame(columns=["dni", "apellido", "nombre"])
                    st.sidebar.success("¡Base de datos reiniciada con éxito!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error al borrar el archivo: {e}")
            else:
                st.sidebar.error("❌ Debes marcar la casilla de confirmación primero.")
    else:
        st.sidebar.warning("Aún no hay asistencias registradas.")
