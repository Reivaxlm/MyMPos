import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime

# Desactivar alertas
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_tasa_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # Añadimos un timeout más corto para no bloquear la interfaz
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        response.raise_for_status() # Lanza error si la página no carga
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraemos Dólar y opcionalmente Euro
        tasa_dolar = soup.find('div', id='dolar').strong.text.strip().replace(',', '.')
        
        tasa_final = float(tasa_dolar)
        
        # LOG sugerido: Guardar en DB aquí (db.actualizar_tasa(tasa_final))
        return tasa_final

    except Exception as e:
        print(f"[{datetime.now()}] Error BCV: {e}")
        # Aquí podrías retornar la última tasa guardada en tu DB
        return None

def formatear_moneda(monto):
    """Convierte 1234.5 a 1.234,50"""
    return "{:,.2f}".format(monto).replace(",", "X").replace(".", ",").replace("X", ".")