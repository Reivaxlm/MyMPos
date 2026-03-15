from database import Database
from decimal import Decimal
from modulo_factura import generar_pdf_cierre

def realizar_cierre(usuario_id):
    db = Database()
    datos = db.obtener_cierre_integral(usuario_id)
    
    # Obtenemos nombre real del usuario de tu tabla public.usuarios
    cajero_nombre = "Cajero"
    with db.get_cursor() as cur:
        cur.execute("SELECT nombre FROM public.usuarios WHERE id = %s", (usuario_id,))
        res = cur.fetchone()
        if res: cajero_nombre = res[0]
    
    # Acumuladores
    totales = {"VENTA_EFECTIVO": 0, "ENTRADAS": 0, "SALIDAS": 0}
    for cat, sub, monto in datos:
        if cat == 'VENTA' and sub == 'Efectivo': 
            totales["VENTA_EFECTIVO"] += Decimal(str(monto))
        elif cat == 'CAJA_CHICA':
            if sub == 'ENTRADA': totales["ENTRADAS"] += Decimal(str(monto))
            if sub == 'SALIDA': totales["SALIDAS"] += Decimal(str(monto))
            
    efectivo_esperado = totales["VENTA_EFECTIVO"] + totales["ENTRADAS"] - totales["SALIDAS"]
    
    # 4. Generar PDF pasando el nombre real
    return generar_pdf_cierre(cajero_nombre, totales, efectivo_esperado)