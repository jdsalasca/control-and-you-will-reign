# Lecciones aprendidas automatizando navegadores con sesión

Cada lección nació de un fallo real. Están ordenadas por cuánto duelen.

---

## 1. Las cookies de sesión mueren con el proceso

**Síntoma:** entras al sitio, funciona; al día siguiente todo redirige al login.

**Causa:** muchas plataformas emiten cookies de sesión (sin `Expires`), que viven en memoria del proceso del navegador. Cerrar la ventana las borra.

**Regla:** un navegador vivo, persistente, que no se cierre entre comandos.

---

## 2. Playwright ocupa el endpoint CDP completo

**Síntoma:** `connect_over_cdp("http://127.0.0.1:9223")` desde otro proceso se queda colgado en `<ws connected>` y expira.

**Causa:** el navegador lanzado por Playwright ya tiene un cliente a nivel de navegador. Chrome atiende uno solo.

**Regla:** no te adjuntes desde fuera. Usa una **cola de trabajos en disco**: el proceso dueño del navegador ejecuta y devuelve la salida.

```
CLI  --escribe-->  %TEMP%/browser_engine/123.job
serve --lee----->  ejecuta con el contexto vivo
CLI  <--lee------  %TEMP%/browser_engine/123.out
```

---

## 3. Un proceso hijo muere con su terminal

**Síntoma:** el navegador «se cierra solo» a las pocas horas.

**Causa:** el proceso se lanzó como hijo de una shell con límite de tiempo; al expirar, se mata el árbol.

**Regla:** lánzalo desacoplado.

```powershell
Start-Process -FilePath "python" -ArgumentList "browser_engine.py","serve" `
  -RedirectStandardOutput serve.log -RedirectStandardError serve.err -WindowStyle Hidden
```

---

## 4. Los pings no evitan el corte del servidor

**Síntoma:** con ping cada 15 minutos, la sesión igual cae a las 03:04.

**Causa:** el servidor invalida la sesión por política propia (duración absoluta, purga nocturna). No es inactividad.

**Regla:** el ping mantiene viva la sesión activa, pero la única defensa real es **relogin automático** con credenciales guardadas por el usuario.

---

## 5. Cada host tiene su propia sesión

**Síntoma:** el portal está autenticado, pero la URL directa del aula cae al login.

**Causa:** cada subdominio es otra instancia con su propia cookie. La autenticación cruzada ocurre al entrar por el enlace del portal (redirección con token).

**Regla:** entra siempre por el portal y deja que él abra el host; después navega dentro.

---

## 6. Las pestañas en blanco rompen la detección

**Síntoma:** «no abrió la página» aunque la página está abierta; se acumulan pestañas.

**Causa:** `window.open()` crea una pestaña vacía antes de navegar; si algo falla queda `about:blank`. Y detectar «pestaña nueva» comparando **URLs** falla cuando dos comparten dirección.

**Regla:** compara **objetos de página**, no URLs.

```python
antes = list(ctx.pages)
disparar_apertura()
nuevas = [pg for pg in ctx.pages if pg not in antes]
```

Y limpia `about:blank` y duplicadas al terminar, nunca la pestaña de trabajo.

---

## 7. El iframe equivocado se traga lo que escribes

**Síntoma:** escribes el cuerpo de un correo, el script dice «ok», el campo queda vacío.

**Causa:** la página tenía dos iframes (el editor y un widget de accesibilidad). Se escribió en el primero.

**Regla:** elige el iframe por identidad, no por orden.

```python
for fr in page.frames:
    if (fr.frame_element().get_attribute("id") or "").endswith("_ifr"):
        ...
```

---

## 8. Los editores enriquecidos guardan su propio modelo

**Síntoma:** el texto aparece en pantalla, pero al guardar se pierde.

**Causa:** TinyMCE/Atto mantienen su modelo interno y al guardar envían **eso**, no el DOM.

**Regla:** usa la API del editor.

```javascript
tinymce.activeEditor.setContent(html);
tinymce.activeEditor.save();
```

---

## 9. Las SPA ignoran eventos sintéticos

**Síntoma:** `element.click()` o `dispatchEvent(new MouseEvent('click'))` no hacen nada.

**Causa:** frameworks (Svelte, Ember, React con synthetic events) exigen eventos confiables o usan delegación por puntero.

**Regla:** clic real de Playwright (`locator.click(force=True)`), nunca `evaluate("el.click()")`.

---

## 10. Arrastrar no siempre es arrastrar

**Síntoma:** `drag_to()` no coloca la ficha.

**Causa:** la app simula arrastre pero acepta **clic en origen y clic en destino**.

**Regla:** antes de pelear con el drag, prueba la secuencia de dos clics y mira las clases/cursor (`cursor: move` sugiere arrastre, pero no lo garantiza).

---

## 11. Deja que la app te diga si acertaste

**Síntoma:** hay que adivinar la respuesta correcta.

**Causa:** se intenta resolver por conocimiento cuando la interfaz ya expone el resultado.

**Regla:** busca clases de estado (`*-correct`, `*-done`, `disabled`) y avanza con esa señal, no con tu suposición.

---

## 12. La fuerza bruta destruye estado

**Síntoma:** tras varios intentos, el ejercicio queda sin fichas y sin solución.

**Causa:** cada intento consumía una ficha.

**Regla:** si la acción no es reversible, no la repitas a ciegas. Verifica el estado antes y después, y detente al primer «sin avance».

---

## 13. Subir archivos en gestores tipo Moodle

Secuencia que funciona:

```
.fp-btn-add a           -> abre el selector
"Subir un archivo"      -> cambia a la pestaña de subida
input[type=file]        -> set_input_files(ruta)
"Subir este archivo"    -> confirma
"Guardar cambios"       -> persiste
```

---

## 14. PDF de una página con sesión

`page.pdf()` solo funciona en headless. Con navegador visible usa CDP:

```python
cdp = ctx.new_cdp_session(page)
datos = cdp.send("Page.printToPDF", {"printBackground": True})
Path("salida.pdf").write_bytes(base64.b64decode(datos["data"]))
```

---

## 15. Verifica con el artefacto, no con el log

**Síntoma:** «cuerpo escrito», «adjunto cargado», «listo»… y el resultado está vacío.

**Causa:** el script reporta su intención, no el estado del sistema.

**Regla:** después de guardar, **reabre** y extrae el texto (o descarga el archivo) y compara. Si no puedes pegar la evidencia, no está hecho.
