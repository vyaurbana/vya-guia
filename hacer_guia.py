# -*- coding: utf-8 -*-
"""
HACER LA GUÍA DE VYA PLAYER (EPG)
Descarga la guía de programación española gratuita de EPG_dobleM (unos 35 MB),
se queda solo con lo que hace falta (de 2 horas antes a 24 horas después)
y la guarda en «guia.json», un archivo pequeño que leen las teles.
Lo ejecuta GitHub solo, varias veces al día (ver .github/workflows/guia.yml).
"""
import gzip, json, re, time, unicodedata, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

ORIGEN = "https://raw.githubusercontent.com/davidmuma/EPG_dobleM/master/guiatv.xml.gz"
HORAS_ATRAS = 2       # programas que ya han empezado
HORAS_DELANTE = 24    # programas de las próximas horas
HORAS_CON_DESCRIPCION = 8   # solo los programas cercanos llevan descripción (para que pese poco)
LARGO_DESCRIPCION = 220

def normalizar(nombre):
    """Convierte el nombre de un canal en una «clave» para poder emparejarlo con las listas.
    Ejemplo: «ES | M+ Estrenos FHD» -> «MPLUSESTRENOS». (En las teles se hace exactamente igual.)"""
    s = unicodedata.normalize("NFD", str(nombre or "").upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")          # quita tildes
    s = re.sub(r"^\s*\|?\s*[A-Z]{2,3}\s*[|:]\s*", " ", s)                # quita «ES |» del principio
    s = s.replace("+", " PLUS ")
    s = re.sub(r"\b(4K|UHD|FHD|HD|SD|HEVC|H265|1080P?|720P?)\b", " ", s)  # quita la calidad
    return re.sub(r"[^A-Z0-9]", "", s)

def limpiar(texto):
    """Quita las marcas de color tipo [COLOR gold] y los espacios sobrantes."""
    texto = re.sub(r"\[/?COLOR[^\]]*\]", "", texto or "")
    return re.sub(r"\s+", " ", texto).strip()

def hora(texto):
    """«20261107065900 +0100» -> segundos desde 1970."""
    return int(datetime.strptime(texto.strip(), "%Y%m%d%H%M%S %z").timestamp())

def texto_es(nodo, etiqueta):
    """El texto en español de una etiqueta (title, desc…), o el primero que haya."""
    elegido = None
    for e in nodo.findall(etiqueta):
        if e.get("lang") == "es":
            return e.text or ""
        elegido = elegido if elegido is not None else (e.text or "")
    return elegido or ""

def main():
    ahora = int(time.time())
    desde, hasta = ahora - HORAS_ATRAS * 3600, ahora + HORAS_DELANTE * 3600
    datos = gzip.decompress(urllib.request.urlopen(ORIGEN, timeout=120).read())
    raiz = ET.fromstring(datos)

    nombres = {}   # id del canal en la guía -> nombre que se ve
    for c in raiz.findall("channel"):
        nombres[c.get("id")] = (c.findtext("display-name") or c.get("id")).strip()

    canales = {}   # clave -> lista de programas [inicio, fin, título, descripción]
    for p in raiz.findall("programme"):
        try:
            ini, fin = hora(p.get("start")), hora(p.get("stop"))
        except Exception:
            continue
        if fin < desde or ini > hasta:
            continue
        titulo = limpiar(texto_es(p, "title"))
        desc = limpiar(texto_es(p, "desc")).lstrip("· ")
        if ini > ahora + HORAS_CON_DESCRIPCION * 3600:
            desc = ""
        if len(desc) > LARGO_DESCRIPCION:
            desc = desc[:LARGO_DESCRIPCION].rsplit(" ", 1)[0] + "…"
        id_canal = p.get("channel")
        for clave in {normalizar(id_canal), normalizar(nombres.get(id_canal, id_canal))}:
            if clave:
                canales.setdefault(clave, []).append([ini, fin, titulo, desc])

    for lista in canales.values():
        lista.sort(key=lambda x: x[0])
    salida = {"generada": ahora, "canales": canales}
    with open("guia.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    print("Canales con guía:", len(canales))

if __name__ == "__main__":
    main()
