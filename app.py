import os
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import streamlit as st

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

                if conceptos is not None:
                    for concepto in conceptos.findall('cfdi:Concepto', ns):
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
                    'Item No.': '',
                    'Vendor Name': nombre_emisor,
                    'Invoice No.': folio,
                    'Subtotal': f"${subtotal:,.2f}",
                    'IVA': f"${iva:,.2f}",
                    'ISR/IVA RETENIDO': f"${isr:,.2f}",
                    'Total': f"${total:,.2f}",
                    'Reviewed By': '',
                    'Approved By': '',
                    'Corp Approval': '',
                    'Description': '',
                    'P.O.': '',
                    'Payment Terms': '',
                    'Invoice date': fecha_formateada,
                    'Due date': '',
                    'PO Date': '',
                    'Receip date': '',
                    'Delivery time': '',
                    'Currency': moneda.upper() if moneda else ''
                }

                tabla.append(fila)

            except Exception as e:
                print(f"❌ Error en {archivo}: {e}")

    return tabla

def main():
    # Título azul marino
    st.markdown(
        """
        <h1 style='color: navy;'>Cash Request</h1>
        """,
        unsafe_allow_html=True
    )

    archivos = st.file_uploader("Sube tus archivos XML", type=["xml"], accept_multiple_files=True)

    if archivos:
        carpeta_temp = "xmls_temp"
        os.makedirs(carpeta_temp, exist_ok=True)

        # Limpiar carpeta antes de guardar
        for f in os.listdir(carpeta_temp):
            os.remove(os.path.join(carpeta_temp, f))

        for archivo in archivos:
            with open(os.path.join(carpeta_temp, archivo.name), "wb") as f:
                f.write(archivo.getbuffer())

        tabla = procesar_xml(carpeta_temp)
        df = pd.DataFrame(tabla)

        # Agregar encabezado extra como fila al inicio
        encabezado_extra = {
            'Item No.': '',
            'Vendor Name': 'Wattera Cash Request',
            'Invoice No.': ' / /',
            'Subtotal': '',
            'IVA': '',
            'ISR/IVA RETENIDO': '',
            'Total': '',
            'Reviewed By': '',
            'Approved By': '',
            'Corp Approval': '',
            'Description': '',
            'P.O.': '',
            'Payment Terms': '',
            'Invoice date': '',
            'Due date': '',
            'PO Date': '',
            'Receip date': '',
            'Delivery time': '',
            'Currency': ''
        }

        df = pd.concat([pd.DataFrame([encabezado_extra]), df], ignore_index=True)

        # Función para limpiar valores de dinero y convertir a float
        def limpiar_valor(valor):
            try:
                return float(str(valor).replace("$", "").replace(",", ""))
            except:
                return 0

        suma_total = sum(limpiar_valor(t) for t in df['Total'])

        # Crear fila de suma total para agregar al final
        fila_suma = {
            'Item No.': '',
            'Vendor Name': '',
            'Invoice No.': '',
            'Subtotal': '',
            'IVA': '',
            'ISR/IVA RETENIDO': '',
            'Total': f"${suma_total:,.2f}",
            'Reviewed By': '',
            'Approved By': '',
            'Corp Approval': '',
            'Description': '',
            'P.O.': '',
            'Payment Terms': '',
            'Invoice date': '',
            'Due date': '',
            'PO Date': '',
            'Receip date': '',
            'Delivery time': '',
            'Currency': ''
        }

        df = pd.concat([df, pd.DataFrame([fila_suma])], ignore_index=True)

        # Estilos para la tabla: 
        # Encabezados con fondo gris y negrita, suma con fondo amarillo en Total
        def highlight_totals(row):
            if row.name == len(df) - 1:  # última fila (suma)
                return ['background-color: yellow; font-weight: bold;' if col == 'Total' else '' for col in df.columns]
            return ['' for _ in df.columns]

        # Streamlit muestra el DataFrame con estilos
        st.dataframe(df.style.set_table_styles(
            [{'selector': 'thead th',
              'props': [('background-color', '#d3d3d3'), ('color', 'black'), ('font-weight', 'bold'), ('text-align', 'center')]}]
            ).apply(highlight_totals, axis=1), use_container_width=True)

if __name__ == "__main__":
    main()

