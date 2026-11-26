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

## Estrategia que funciona

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
