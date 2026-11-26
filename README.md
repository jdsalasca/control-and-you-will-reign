# control-and-you-will-reign

Un navegador real, una sola sesión, muchos comandos.

Este repositorio nace de un problema muy concreto: automatizar páginas que exigen
sesión iniciada sin perder esa sesión a cada rato. Un navegador por comando no sirve
(las cookies de sesión mueren al cerrar). Adjuntarse por CDP a un Chrome lanzado por
Playwright tampoco (el endpoint del navegador admite un solo cliente y el segundo se
cuelga). Y un proceso hijo de una terminal muere con ella.

La solución es pequeña: **un proceso dueño del navegador + una cola de trabajos en
disco**. Todo lo demás son detalles que están documentados aquí para no volver a
tropezar.

## Arranque

```powershell
python engine/browser_engine.py serve --url https://ejemplo.com
```

En otra terminal:

```powershell
python engine/browser_engine.py estado
python engine/browser_engine.py js --expr "() => document.title"
python engine/browser_engine.py clic --texto "Entrar"
python engine/browser_engine.py shot --salida captura.png
python engine/browser_engine.py tabs --limpiar
```

La primera vez se inicia sesión a mano en la ventana; a partir de ahí el perfil
persistente la conserva.

## Arquitectura

```
┌──────────────┐   .job    ┌───────────────────────┐
│  cualquier   │ ────────► │  serve (dueño del     │
│  comando     │           │  navegador Playwright)│
│  (CLI)       │ ◄──────── │  ejecuta y responde   │
└──────────────┘   .out    └───────────┬───────────┘
                                       │
                              ┌────────▼────────┐
                              │ Chrome (perfil  │
                              │ persistente)    │
                              └─────────────────┘
```

- `serve` mantiene el navegador y refresca una marca `alive` cada 0,5 s.
- Cada comando deja `%TEMP%/browser_engine/<id>.job` y espera `<id>.out`.
- Si no hay `serve`, el comando intenta CDP directo (útil si tú lanzas Chrome con
  `--remote-debugging-port`).

## Documentación

- [`docs/LESSONS.md`](docs/LESSONS.md) — 15 lecciones, cada una con síntoma, causa y regla.
- [`docs/RECIPES.md`](docs/RECIPES.md) — recetas copiables y anti-patrones.

## Límites conocidos

- **Las sesiones del servidor expiran igual.** El ping mantiene activa la sesión,
  pero si el servidor la invalida por política, la única salida es relogin automático
  con credenciales que el usuario guarde.
- **Las SPA ignoran eventos sintéticos.** Hay que usar clics reales; `element.click()`
  por JavaScript no cuenta.
- **Los editores enriquecidos guardan su propio modelo.** Escribir en el iframe no
  persiste: hay que usar su API.
- **No hay automatización honesta de ejercicios con voz.** Si la tarea exige hablar,
  la graba la persona.

## Estado del proyecto

Motor estable y probado en sesiones largas sobre un campus Moodle (login, clases,
correo interno con editor TinyMCE y gestor de archivos) y sobre una app de idiomas
con ejercicios de emparejar.

## Licencia

MIT.
