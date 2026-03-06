import re
from decimal import Decimal

def parse_monto(valor):
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float, Decimal)):
        return float(valor)
    s = str(valor).strip()
    if s == "":
        return 0.0
    # Eliminar símbolos de moneda y espacios
    s = s.replace(' ', '').replace('$', '').replace('US$', '').replace('Bs.', '').replace('Bs', '')
    
    # Lógica para detectar decimales y miles
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        # Si solo hay coma, asumimos que es el decimal (formato latino)
        s = s.replace(',', '.')
        
    try:
        return float(s)
    except ValueError:
        return 0.0