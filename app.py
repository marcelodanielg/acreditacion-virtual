def leer_asistencias_sheets():
    columnas_base = ["dni", "nombre", "apellido", "fecha_hora_entrada", "fecha_hora_salida", "minutos_conectado"]
    try:
        # Intentamos leer la planilla
        df = conn.read(ttl=0)
        
        # Si df es None o está vacío, o no tiene columnas, retornamos un DF base vacío
        if df is None or df.empty or len(df.columns) == 0:
            st.sidebar.warning("La planilla está vacía o no tiene encabezados.")
            return pd.DataFrame(columns=columnas_base)
        
        # Limpieza de nombres de columnas
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Verificamos si al menos existe la columna 'dni'
        if "dni" not in df.columns:
            st.sidebar.error("Error: La planilla no tiene la columna 'dni'.")
            return pd.DataFrame(columns=columnas_base)
            
        return df
        
    except Exception as e:
        st.sidebar.error(f"Error de conexión: {e}")
        return pd.DataFrame(columns=columnas_base)
