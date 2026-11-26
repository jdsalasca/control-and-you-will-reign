"""Solver por visión para ejercicios de emparejar palabra-imagen en apps de canvas.

Idea: cuando la app dibuja en un <canvas>, los nodos DOM no sirven para pulsar.
Entonces se trabaja con la imagen: se detectan las cajas por color, se lee su texto
con OCR, se decide la respuesta y se pulsa por coordenadas.

Probado contra Mondly (Ember + canvas). Resultado: dos pares resueltos seguidos
sin intervención.

Requisitos: pillow, pytesseract, tesseract-ocr.
"""

from __future__ import annotations

import io

import pytesseract
from PIL import Image

# Colores observados en Mondly (RGB aproximados)
ES_NARANJA = lambda r, g, b: r > 190 and 80 < g < 175 and b < 90  # palabra a colocar
ES_AZUL = lambda r, g, b: r < 90 and 110 < g < 190 and b > 200  # etiqueta disponible
ES_VERDE = lambda r, g, b: r < 120 and g > 140 and b < 120  # etiqueta acertada

VOCABULARIO_EN_ES = {
    "green": "verde",
    "white": "blanco",
    "black": "negro",
    "blue": "azul",
    "red": "rojo",
    "yellow": "amarillo",
    "orange": "naranja",
    "pink": "rosa",
    "snow": "nieve",
    "rain": "lluvia",
    "sun": "sol",
    "cloud": "nube",
    "wind": "viento",
    "grass": "hierba",
    "tree": "arbol",
    "flower": "flor",
    "sky": "cielo",
    "sea": "mar",
    "hot": "caliente",
    "cold": "frio",
}


def cajas_por_color(img, regla, minimo=800, paso=3):
    """Rectángulos (x0, y0, x1, y1) de las zonas que cumplen la regla de color."""
    ancho, alto = img.size
    pix = img.load()
    visto, cajas = set(), []
    for y in range(0, alto, paso):
        for x in range(0, ancho, paso):
            if (x, y) in visto:
                continue
            r, g, b = pix[x, y]
            if not regla(r, g, b):
                continue
            pila = [(x, y)]
            visto.add((x, y))
            x0 = x1 = x
            y0 = y1 = y
            cuenta = 0
            while pila:
                cx, cy = pila.pop()
                cuenta += 1
                x0, x1 = min(x0, cx), max(x1, cx)
                y0, y1 = min(y0, cy), max(y1, cy)
                for dx, dy in ((paso, 0), (-paso, 0), (0, paso), (0, -paso)):
                    nx, ny = cx + dx, cy + dy
                    if (
                        nx < 0
                        or ny < 0
                        or nx >= ancho
                        or ny >= alto
                        or (nx, ny) in visto
                    ):
                        continue
                    rr, gg, bb = pix[nx, ny]
                    if regla(rr, gg, bb):
                        visto.add((nx, ny))
                        pila.append((nx, ny))
            if cuenta * paso * paso >= minimo:
                cajas.append((x0, y0, x1, y1))
    return cajas


def leer_texto(img, caja, escala=3):
    x0, y0, x1, y1 = caja
    trozo = img.crop((x0, y0, x1, y1)).resize(((x1 - x0) * escala, (y1 - y0) * escala))
    texto = pytesseract.image_to_string(trozo, config="--psm 7").strip().lower()
    return "".join(c for c in texto if c.isalpha())


def resolver_pareo(pagina, max_pasos=20, vocabulario=None, registrar=print):
    """Resuelve la secuencia de emparejamientos de una pantalla.

    `pagina` es una página de Playwright. Devuelve el número de pares acertados.
    """
    vocabulario = vocabulario or VOCABULARIO_EN_ES
    acertados = 0
    for paso in range(max_pasos):
        png = pagina.screenshot()
        img = Image.open(io.BytesIO(png)).convert("RGB")
        dpr = pagina.evaluate("() => window.devicePixelRatio") or 1
        alto = img.size[1]

        palabras = [
            c
            for c in cajas_por_color(img, ES_NARANJA)
            if (c[2] - c[0]) > 180 and 0.42 * alto < (c[1] + c[3]) / 2 < 0.60 * alto
        ]
        palabras.sort(key=lambda c: c[2] - c[0], reverse=True)
        etiquetas = [c for c in cajas_por_color(img, ES_AZUL) if (c[2] - c[0]) > 150]
        if not palabras or not etiquetas:
            registrar(f"paso {paso}: sin palabra o sin etiquetas; fin")
            break

        palabra = leer_texto(img, palabras[0])
        espanol = vocabulario.get(palabra)
        registrar(f"paso {paso}: OCR '{palabra}' -> '{espanol}'")
        if not espanol:
            break

        objetivo = next((c for c in etiquetas if leer_texto(img, c) == espanol), None)
        if objetivo is None:
            registrar(f"paso {paso}: no encontre la etiqueta '{espanol}'")
            break

        cx = (objetivo[0] + objetivo[2]) / 2 / dpr
        cy = (objetivo[1] + objetivo[3]) / 2 / dpr
        pagina.mouse.click(cx, cy)
        pagina.wait_for_timeout(2600)
        acertados += 1
        registrar(f"paso {paso}: clic ({int(cx)},{int(cy)})")
    return acertados
