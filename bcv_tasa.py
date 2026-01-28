import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime

# Desactivar alertas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_tasa_bcv(self=None):
    # URLs de respaldo (DolarApi es más rápida y estable que el BCV directo)
    url_bcv = "https://www.bcv.org.ve/"
    url_api = "https://ve.dolarapi.com/v1/dolares/oficial"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    # 1. INTENTO CON API (Más rápido)
    try:
        response = requests.get(url_api, timeout=3)
        if response.status_code == 200:
            data = response.json()
            tasa = float(data['promedio'])
            print(f"[{datetime.now()}] Tasa obtenida vía API: {tasa}")
            return tasa
    except:
        pass # Si falla la API, intentamos con el BCV directo

    # 2. INTENTO CON BCV DIRECTO (Tu código original mejorado)
    try:
        response = requests.get(url_bcv, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tasa_dolar = soup.find('div', id='dolar').strong.text.strip().replace(',', '.')
        tasa_final = float(tasa_dolar)
        
        print(f"[{datetime.now()}] Tasa obtenida vía BCV: {tasa_final}")
        return tasa_final

    except Exception as e:
        print(f"[{datetime.now()}] Error crítico conectando al BCV: {e}")
        
        # 3. PLAN DE EMERGENCIA (Retornar última tasa o valor fijo)
        # Intentamos obtener la tasa que ya tenemos en el programa
        if self and hasattr(self, 'tasa') and self.tasa:
            return self.tasa
            
        return 45.00 # Valor de emergencia (ajústalo al actual)

def formatear_moneda(monto):
    """Convierte 1234.5 a 1.234,50"""
    return "{:,.2f}".format(monto).replace(",", "X").replace(".", ",").replace("X", ".")