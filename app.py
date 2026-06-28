def leer_asistencias_sheets():
    columnas_base = ["dni", "nombre", "apellido", "fecha_hora_entrada", "fecha_hora_salida", "minutos_conectado"]
    try:
        df = conn.read(ttl=0)
        
        # DEBUG: Esto mostrará en pantalla qué está viendo la app
        if df is not None:
            st.sidebar.write("Columnas detectadas:", df.columns.tolist())
        
        if df is None or df.empty:
            return pd.DataFrame(columns=columnas_base)
        
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        for col in columnas_base:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.sidebar.error(f"Error al leer: {e}")
        return pd.DataFrame(columns=columnas_base)
