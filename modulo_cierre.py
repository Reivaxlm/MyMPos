from database import Database
from modulo_factura import generar_pdf_cierre


def realizar_cierre():
    db = Database()
    # Usamos el nuevo método que agregaste a database.py
    resultados = db.obtener_totales_cierre_hoy() 
    
    if not resultados:
        return "No hay ventas hoy para cerrar."
    
    # Convertimos los resultados a diccionario
    totales_dict = {fila[0]: fila[1] for fila in resultados}
    gran_total = sum(totales_dict.values())
    
    # Generamos el PDF
    return generar_pdf_cierre("Cajero", totales_dict, gran_total)