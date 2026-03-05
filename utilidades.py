import re
from decimal import Decimal

def parse_monto(valor):
    """Tu lógica original para limpiar $, Bs y comas de los montos"""
    if valor is None: return 0.0
    if isinstance(valor, (int, float, Decimal)): return float(valor)
    s = str(valor).strip()
    if s == "": return 0.0
    s = s.replace(' ', '').replace('$', '').replace('Bs.', '').replace('Bs', '')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
        else: s = s.replace(',', '')
    elif ',' in s: s = s.replace('.', '').replace(',', '.')
    s = re.sub(r'[^0-9\.\-]', '', s)
    try: return float(s)
    except: return 0.0