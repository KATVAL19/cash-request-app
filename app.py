import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import streamlit as st
from io import BytesIO

# Namespace SAT
ns = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
}

def procesar_xml(carpeta):
    tabla = []

    for archivo in os.listdir(carpeta):
        if archivo.endswith('.xml'):
            ruta = os.path.join(carpeta, archivo)
            try:
                tree = ET.parse(ruta)
                root = tree.getroot()

                emisor = root.find('cfdi:Emisor', ns)
                nombre_emisor = emisor.attrib.get('Nombre', '') if emisor is not None else ''

                folio = root.attrib.get('Folio', '')
                subtotal = float(root.attrib.get('SubTotal', '0'))
                total = float(root.attrib.get('Total', '0'))
                moneda = root.attrib.get('Moneda', '')
                fecha = root.attrib.get('Fecha', '')[:10]  # YYYY-MM-DD

                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if fecha else None
                fecha_formateada = fecha_obj.strftime('%m/%d/%Y') if fecha_obj else ''

                conceptos = root.find('cfdi:Conceptos', ns)
                iva = 0.0
                isr = 0.0
                descripciones = []

                if conceptos is not None:
                    for concepto in conceptos.findall('cfdi:Concepto', ns):
                        descripcion = concepto.attrib.get('Descripcion', '')
                        if descripcion:
                            descripciones.append(descripcion.strip())

                        impuestos = concepto.find('cfdi:Impuestos', ns)
                        if impuestos is not None:
                            traslados = impuestos.find('cfdi:Traslados', ns)
                            if traslados is not None:
                                for traslado in traslados.findall('cfdi:Traslado', ns):
                                    if traslado.attrib.get('Impuesto') == '002':
                                        iva += float(traslado.attrib.get('Importe'))

                            retenciones = impuestos.find('cfdi:Retenciones', ns)
                            if retenciones is not None:
                                for retencion in retenciones.findall('cfdi:Retencion', ns):
                                    if retencion.attrib.get('Impuesto') == '001':
                                        isr += float(retencion.attrib.get('Importe'))

                fila = {
                    'Item No.': '', 'Vendor Name': nombre_emisor, 'Invoice No.': folio,
                    'Subtotal': f"${subtotal:,.2f}", 'IVA': f"${iva:,.2f}", 'ISR/IVA RETENIDO': f"${isr:,.2f}",
                    'Total': f"${total:,.2f}", 'Reviewed By': '', 'Approved By': '', 'Corp Approval': '',
                    'Description': ' | '.join(descripciones), 'P.O.': '', 'Payment Terms': '',
                    'Invoice date': fecha_formateada, 'Due date': '', 'PO Date': '',
                    'Receip date': '', 'Delivery time': '', 'Currency': ''
                }
                tabla.append(fila)

            except Exception as e:
                st.error(f"❌ Error en {archivo}: {e}")

    return tabla

def depurar_excel(df_bruto):
    df_depurado = df_bruto[
        ~df_bruto.iloc[:, 0].astype(str).str.contains(
            "Dollars For Week|Week Starting", na=False, case=False
        )
    ].copy()

    df_depurado.dropna(how='all', inplace=True)
    
    return df_depurado.reset_index(drop=True)

def main():
    st.markdown(
        """
        <h1 style='color: navy;'>App de Gestión de Datos</h1>
        """,
        unsafe_allow_html=True
    )

    # Inicializar el estado de sesión si no existe
    if 'master_df' not in st.session_state:
        st.session_state.master_df = pd.DataFrame()

    tab1, tab2 = st.tabs(["Cash Request", "Depurar Archivo Excel"])

    with tab1:
        st.header("Generar Solicitud de Efectivo")
        archivos = st.file_uploader("Sube tus archivos XML", type=["xml"], accept_multiple_files=True)

        if archivos:
            carpeta_temp = "xmls_temp"
            os.makedirs(carpeta_temp, exist_ok=True)

            for f in os.listdir(carpeta_temp):
                os.remove(os.path.join(carpeta_temp, f))

            for archivo in archivos:
                with open(os.path.join(carpeta_temp, archivo.name), "wb") as f:
                    f.write(archivo.getbuffer())

            tabla = procesar_xml(carpeta_temp)
            df = pd.DataFrame(tabla)

            encabezado_extra = {
                'Item No.': '', 'Vendor Name': 'Wattera Cash Request', 'Invoice No.': ' / /',
                'Subtotal': '', 'IVA': '', 'ISR/IVA RETENIDO': '', 'Total': '',
                'Reviewed By': '', 'Approved By': '', 'Corp Approval': '',
                'Description': '', 'P.O.': '', 'Payment Terms': '',
                'Invoice date': '', 'Due date': '', 'PO Date': '',
                'Receip date': '', 'Delivery time': '', 'Currency': ''
            }
            df = pd.concat([pd.DataFrame([encabezado_extra]), df], ignore_index=True)

            def limpiar_valor(valor):
                try:
                    return float(str(valor).replace("$", "").replace(",", ""))
                except:
                    return 0

            suma_total = sum(limpiar_valor(t) for t in df['Total'])

            fila_suma = {
                'Item No.': '', 'Vendor Name': '', 'Invoice No.': '',
                'Subtotal': '', 'IVA': '', 'ISR/IVA RETENIDO': '',
                'Total': f"${suma_total:,.2f}", 'Reviewed By': '',
                'Approved By': '', 'Corp Approval': '', 'Description': '',
                'P.O.': '', 'Payment Terms': '', 'Invoice date': '',
                'Due date': '', 'PO Date': '', 'Receip date': '',
                'Delivery time': '', 'Currency': ''
            }
            df = pd.concat([df, pd.DataFrame([fila_suma])], ignore_index=True)

            def highlight_totals(row):
                if row.name == len(df) - 1:
                    return ['background-color: yellow; font-weight: bold;' if col == 'Total' else '' for col in df.columns]
                return ['' for _ in df.columns]

            st.dataframe(df.style.set_table_styles(
                [{'selector': 'thead th',
                  'props': [('background-color', '#d3d3d3'), ('color', 'black'), ('font-weight', 'bold'), ('text-align', 'center')]}]
            ).apply(highlight_totals, axis=1), use_container_width=True)

    with tab2:
        st.header("Depurar Archivo Excel")
        st.write("Sube el archivo Excel original para depurarlo.")

        uploaded_file = st.file_uploader("Arrastra aquí el archivo 'NO modificado'", type=["xlsx", "xls", "csv"])

        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_bruto = pd.read_csv(uploaded_file)
                else:
                    df_bruto = pd.read_excel(uploaded_file)

                st.success("✅ Archivo cargado correctamente.")

                st.subheader("Vista previa del archivo sin depurar")
                st.dataframe(df_bruto.head(10))
                
                if st.button("Depurar y Descargar"):
                    df_depurado = depurar_excel(df_bruto)
                    
                    if not df_depurado.empty:
                        # 1. Comparar con el DataFrame maestro para encontrar duplicados
                        if not st.session_state.master_df.empty:
                            merged_df = pd.merge(df_depurado, st.session_state.master_df, how='left', indicator=True)
                            duplicates = merged_df[merged_df['_merge'] == 'both'].iloc[:, :-1]
                            new_data_only = merged_df[merged_df['_merge'] == 'left_only'].iloc[:, :-1]
                        else:
                            # Si el maestro está vacío, todos los datos son nuevos
                            duplicates = pd.DataFrame()
                            new_data_only = df_depurado.copy()

                        # 2. Mostrar los duplicados encontrados
                        if not duplicates.empty:
                            st.warning(f"⚠️ ¡Se encontraron {len(duplicates)} filas duplicadas!")
                            st.subheader("Duplicados Encontrados")
                            st.dataframe(duplicates)
                        
                        # 3. Actualizar la base de datos con los datos nuevos
                        if not new_data_only.empty:
                            st.session_state.master_df = pd.concat([st.session_state.master_df, new_data_only], ignore_index=True)
                            
                            st.success("✅ Nuevos datos agregados a la base de datos.")
                            st.subheader("Nuevos Datos Únicos")
                            st.dataframe(new_data_only)

                            # 4. Preparar el archivo para la descarga
                            output = BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                new_data_only.to_excel(writer, index=False, sheet_name='Sheet1')
                            output.seek(0)
                            
                            st.download_button(
                                label="Descargar Nuevos Datos",
                                data=output,
                                file_name="nuevos_datos_depurados.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.info("ℹ️ El archivo subido no contiene nuevos datos.")
            
            except Exception as e:
                st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
                st.warning("Asegúrate de que el archivo tenga un formato y contenido similar al ejemplo original.")

if __name__ == "__main__":
    main()


