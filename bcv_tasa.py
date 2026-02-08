import requests
from bs4 import BeautifulSoup
from datetime import datetime


def obtener_tasa_bcv():
    """Intenta obtener la tasa desde una API primero y luego desde la web del BCV.
    Retorna `None` si no se puede obtener — el llamador debe usar un fallback local.
    """
    url_api = "https://ve.dolarapi.com/v1/dolares/oficial"
    url_bcv = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 1) Intento con API pública
    try:
        resp = requests.get(url_api, timeout=4)
        resp.raise_for_status()
        data = resp.json()
        tasa = float(data.get('promedio'))
        print(f"[{datetime.now()}] Tasa obtenida vía API: {tasa}")
        return tasa
    except Exception as e:
        print(f"[{datetime.now()}] Falló API DolarApi: {e}")

    # 2) Intento scraping BCV como fallback
    try:
        resp = requests.get(url_bcv, headers=headers, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        nodo = soup.find('div', id='dolar')
        if nodo and nodo.strong:
            tasa_dolar = nodo.strong.text.strip().replace(',', '.')
            tasa_final = float(tasa_dolar)
            print(f"[{datetime.now()}] Tasa obtenida vía BCV: {tasa_final}")
            return tasa_final
    except Exception as e:
        print(f"[{datetime.now()}] Falló scraping BCV: {e}")

    # No pudimos obtener la tasa desde internet
    return None

def formatear_moneda(monto):
    """Convierte 1234.5 a 1.234,50"""
    return "{:,.2f}".format(monto).replace(",", "X").replace(".", ",").replace("X", ".")