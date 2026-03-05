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

def generar_pdf_cierre(cajero, totales_por_metodo, gran_total):
    """Mecanismo para el reporte de cierre (Corte X/Z)"""
    fecha_str = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = f"cierre_{cajero}_{fecha_str}.pdf"
    
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 800, "CORTE DE CAJA")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Cajero: {cajero}")
    c.drawString(50, 755, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    c.line(50, 740, 550, 740)
    c.drawString(50, 720, "MÉTODO")
    c.drawString(450, 720, "MONTO")
    
    y = 700
    for metodo, monto in totales_por_metodo.items():
        c.drawString(50, y, str(metodo))
        c.drawString(450, y, f"$ {monto:.2f}")
        y -= 20
        
    c.line(50, y, 550, y)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y-25, "TOTAL:")
    c.drawString(450, y-25, f"$ {gran_total:.2f}")
    
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(300, y-100, "Firma del Cajero")
    c.line(200, y-90, 400, y-90)
    
    c.save()
    os.startfile(filename)