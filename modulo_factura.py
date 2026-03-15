import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generar_factura_pdf(id_venta, cliente_nom, cliente_id, items, total_usd, total_bs, tasa, metodo):
    """Mecanismo original de PDF extraído de tu main.py"""
    filename = f"factura_{id_venta}_{datetime.now().strftime('%H%M%S')}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "MYMPOS - RECIBO DE VENTA")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Venta #: {id_venta}")
    c.drawString(50, height - 85, f"Cliente: {cliente_nom}")
    c.drawString(50, height - 100, f"ID/Cédula: {cliente_id}")
    c.drawString(50, height - 115, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    y = height - 150
    c.line(50, y+10, 550, y+10)
    c.drawString(50, y, "Producto")
    c.drawString(350, y, "Cant.")
    c.drawString(450, y, "Precio $")
    
    for cod, data in items.items():
        y -= 20
        c.drawString(50, y, str(data['nombre']))
        c.drawString(350, y, str(data['cant']))
        c.drawString(450, y, f"{data['precio']:.2f}")

    y -= 40
    c.line(350, y+15, 550, y+15)
    c.drawString(350, y, f"TOTAL USD: ${total_usd:.2f}")
    c.drawString(350, y-15, f"TOTAL BS: {total_bs:.2f}")
    c.drawString(350, y-30, f"Metodo: {metodo}")
    
    c.save()
    if os.name == 'nt': os.startfile(filename)
    return filename

def generar_pdf_cierre(cajero_nombre, totales, gran_total):
    fecha_dt = datetime.now()
    fecha_str = fecha_dt.strftime("%d-%m-%Y_%H-%M-%S")
    nombre_limpio = cajero_nombre.replace(" ", "_")
    filename = f"cierre_{nombre_limpio}_{fecha_str}.pdf"
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # 1. ENCABEZADO PROFESIONAL
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 50, "REPORTE DE CIERRE DE CAJA")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 65, "Sistema de Gestión de Ventas - MyMPos")
    
    # Información del cajero
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, f"Cajero Responsable:")
    c.setFont("Helvetica", 12)
    c.drawString(180, height - 120, f"{cajero_nombre.upper()}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 135, f"Fecha y Hora:")
    c.setFont("Helvetica", 12)
    c.drawString(180, height - 135, fecha_dt.strftime('%d/%m/%Y %H:%M:%S'))
    
    # 2. TABLA DE DETALLES
    y = height - 180
    c.setStrokeColorRGB(0.7, 0.7, 0.7) # Línea gris suave
    c.line(50, y + 15, width - 50, y + 15)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "CONCEPTO")
    c.drawRightString(width - 50, y, "MONTO (USD)")
    
    c.setStrokeColorRGB(0, 0, 0)
    c.line(50, y - 5, width - 50, y - 5)
    
    # Datos
    c.setFont("Helvetica", 12)
    y -= 25
    datos = [
        ("Ventas en Efectivo", totales['VENTA_EFECTIVO']),
        ("Entradas Caja Chica", totales['ENTRADAS']),
        ("Salidas Caja Chica", -totales['SALIDAS'])
    ]
    
    for concepto, monto in datos:
        c.drawString(50, y, concepto)
        c.drawRightString(width - 50, y, f"{float(monto):,.2f}")
        y -= 20
        
    # 3. TOTALIZADOR
    y -= 10
    c.setStrokeColorRGB(0, 0, 0)
    c.line(300, y + 10, width - 50, y + 10) # Línea de suma
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(300, y - 10, "TOTAL ESPERADO:")
    c.drawRightString(width - 50, y - 10, f"$ {float(gran_total):,.2f}")
    
    # 4. PIE DE PÁGINA (Firma)
    c.line(200, 100, 400, 100)
    c.drawCentredString(width/2, 85, "Firma del Cajero")
    
    c.save()
    
    if os.name == 'nt':
        os.startfile(filename)
    return filename