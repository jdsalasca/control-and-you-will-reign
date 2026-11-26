# Mondly (app web): lo que expone por dentro

Investigación hecha sobre una cuenta real, navegador con sesión, en la lección
`601` («Nature's Colours», categoría 6 «Seasons & Weather»).

## Por qué Ember importa

`window.Ember` y `window.require` existen. La app es Ember + webpack, y eso explica
el comportamiento que rompía la automatización:

- Ignora `element.click()` y `dispatchEvent(new MouseEvent(...))`: necesita eventos
  **confiables**. Playwright con `click(force=True)` sí los produce.
- Los estados viven en clases: `d-sol` (ficha), `d-box` (hueco), `d-box-correct`
  (hueco acertado), `d-sol-done` (ficha ya usada). Eso da un canal de verificación
  sin adivinar.

## El endpoint que sirve la lección

```
GET https://api.mondly.com/v2/categories/{categoryId}/lessons/{lessonId}
```

- Devuelve **200** con la sesión del navegador (cookies), sin token adicional.
- Respuesta: `{ lesson: {...}, quizzes: [...] }`.
- `lesson`: `id`, `name`, `difficulty`, `countQuiz`, `countWords`, `countPhrases`,
  `done`, `stars`, `quizzes: [ids]`.
- Cada `quiz`: `id`, `type`, `modifiers`, `wordID`, `alternates: [ids]`,
  `sols: [{key: "..."}]`.

Ejemplo real: lección 601 → **25 quizzes**, 15 palabras, 6 frases.

### Tipos encontrados (lección 601)

| Tipo | Cantidad |
|---|---|
| `T1b` | 4 |
| `C1b`, `T1`, `Q`, `Qb` | 3 cada uno |
| `F` | 2 |
| `D`, `W1b`, `C2b`, `R`, `T2`, `L1`, `T2b` | 1 cada uno |

Eso significa **13 mecánicas distintas** en una sola lección.

## Lo que la API no da

- Los **textos** de las palabras no vienen en claro: `sols` trae claves tipo
  `Hz_F82ljmbVk6HAIpKu9ee0MSImTZD-` y `alternates` trae IDs. La traducción la resuelve
  el bundle del cliente.
- Probados y **no disponibles** (CORS/404): `/v1/words/{id}`, `/v1/words`,
  `/v1/categories/{id}/words`, `/v1/dictionary/{id}`, `/v2/words/{id}`.

Conclusión: los datos sirven para **planificar** (cuántos ejercicios, de qué tipo),
pero la respuesta correcta hay que leerla de la pantalla.

## El hallazgo que lo explica todo: la app dibuja en un canvas

`document.elementFromPoint()` sobre cualquier ficha devuelve **`CANVAS`**. Hay un
canvas de pantalla completa (1040×747 CSS, `pointer-events: auto`) por encima del DOM.

Consecuencias:

1. Los nodos DOM son un esqueleto: sirven para leer texto, pero **no** para pulsar.
2. Los eventos llegan al canvas con `target` vacío; la app hace su propio *hit-test*.
3. `element.click()`, `dispatchEvent` y `locator.click()` sobre fichas **no cambian
   el estado** (el evento se entrega, pero en el nodo equivocado del hit-test).

### Lo que sí funciona: clic por coordenadas

```
page.mouse.click(cssX, cssY)
```

Probado: clic en `(365, 600)` colocó la palabra «white» sobre la imagen «blanco»,
la marcó en verde y la app avanzó a la siguiente palabra.

### Cómo obtener las coordenadas correctas

- `page.screenshot()` devuelve la imagen a **device pixels** (viewport × DPR). Con
  DPR 2 y viewport 1040×747, la imagen sale 2080×1494.
- Coordenada CSS = `pixel_imagen / DPR`.
- Para localizar la ficha: mirar la captura (posición visual) y convertir, o usar
  los rectángulos del DOM **solo como pista** y verificar con una captura posterior.

### Regla de oro

Después de cada clic, captura y compara. Si la pantalla no cambió, la coordenada
está mal: no insistas, recalcula.


### Emparejar (`D`, `W1b`) — resuelto

- Ficha pendiente: `div.d-sol` sin la clase `d-sol-done`.
- Destino: `div.d-box` cuyo texto es la traducción.
- Confirmación: el destino pasa a `d-box-correct`.
- Secuencia: clic real en la ficha, clic real en el destino.

### Ordenar oración («Translate this sentence») — en análise

Estructura observada:

| Parte | Selector |
|---|---|
| Frase original | `.words` (p. ej. «The grass is green .») |
| Respuesta en construcción | `.selected-row .tokens` |
| Banco de fichas | `.tokens .token-container > .token` |

Hallazgo incómodo: el clic real sobre `.token-container` **no incorpora la ficha**
(el DOM no cambia y `Check` no avanza). Hipótesis: la ficha escucha
`pointerdown`/`pointerup` con delegación, o exige clic sobre `.token` interior
con coordenadas exactas.

Siguiente paso para quien lo retome: probar `page.mouse.click(x, y)` sobre el
centro de `.token`, o `dispatchEvent(new PointerEvent('pointerdown'))` seguido de
`pointerup` sobre el mismo nodo.


1. **Leer el estado del DOM**, no adivinarlo: `div.d-sol` sin `d-sol-done` es la ficha
   pendiente; `div.d-box` con texto es el destino.
2. **Clic real**: ficha → destino. Verificar con `d-box-correct`.
3. **Parar al primer «sin avance».** Repetir a ciegas consume fichas y deja el
   ejercicio irresoluble (pasó y quedó documentado).
4. **Un handler por tipo.** El emparejar (`D`/`W1b`) ya está resuelto; ordenar
   oraciones, escuchar y pronunciar requieren su propio análisis.

## Tipos que no se automatizan con honestidad

- Pronunciación y conversación por voz: requieren la voz de la persona.
- Escuchar y elegir: se puede acertar sin oír, pero no es evidencia de práctica.

## Estado

| Elemento | Estado |
|---|---|
| Endpoint de lección | Verificado |
| Lectura de estado del DOM | Verificado |
| Handler de emparejar | Implementado y probado (4/4) |
| Handler de ordenar oraciones | Pendiente |
| Resto de tipos | Pendiente |
| Voz | No aplica |
