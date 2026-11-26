# Tipos de ejercicio en apps de idiomas: qué se puede automatizar y qué no

Registro de lo observado en Mondly (SPA web, Ember) y extrapolable a Duolingo,
Babbel y similares.

| Tipo | Mecánica real | ¿Automatizable? | Cómo |
|---|---|---|---|
| Emparejar palabra ↔ imagen/texto («Move the word to the correct answer») | Una ficha inglesa visible; hay que pulsar la ficha y luego la caja española | **Sí** | Clic real en `div.d-sol`, luego clic real en `div.d-box` cuyo texto sea la traducción. Confirmación: la caja pasa a `d-box-correct` |
| Ordenar palabras de una oración | Fichas en banco; se construyen en una fila | Parcial | Requiere conocer el orden correcto; después son clics secuenciales |
| Elegir traducción entre opciones | Botones o tarjetas | Sí | Clic real en la opción; validar por cambio de pantalla |
| Escuchar y elegir | Audio + opciones | Parcial | Se puede elegir sin oír, pero es azar: no es evidencia honesta |
| Pronunciar / repetir | Micrófono | **No** | Requiere voz de la persona |
| Conversación libre con bot | Texto o voz | **No** (voz) / Parcial (texto) | El bot evalúa coherencia; no es mecánico |

## Reglas que salieron de esto

1. **La app te dice si acertaste.** Usa sus clases de estado (`d-box-correct`,
   `*-done`, `disabled`) en lugar de intentar adivinar por tu cuenta.
2. **Clic real, no sintético.** Ember ignora `element.click()` y
   `dispatchEvent(new MouseEvent(...))`. Playwright con `force=True` sí funciona.
3. **No fuerces con arrastre si acepta dos clics.** `drag_to()` puede no disparar
   los manejadores; prueba clic en origen + clic en destino.
4. **No repitas a ciegas acciones no reversibles.** En un ejercicio de emparejar,
   cada intento consumía una ficha; tras varios fallos la pantalla quedaba sin
   solución. Ahora se verifica el estado antes y después de cada acción.
5. **Las lecciones mezclan tipos.** Un solver de un tipo avanza hasta que cambia el
   ejercicio; hay que detectar el cambio y decidir si se sigue o se para.

## Lo que no se automatiza, y por qué está bien

Una tarea cuyo objetivo es *practicar el habla* no se puede cumplir sin hablar.
Simular el 8/8 con una captura editada es fabricar evidencia, y además se cae sola:
el perfil muestra nivel y puntos coherentes con la actividad real.
