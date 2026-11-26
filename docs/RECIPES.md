# Recetas

Fragmentos listos para copiar. Todos asumen el motor de `engine/browser_engine.py`.

## Arrancar y comprobar

```powershell
Start-Process -FilePath "python" -ArgumentList "engine/browser_engine.py","serve","--url","https://sitio.com" `
  -RedirectStandardOutput serve.log -RedirectStandardError serve.err -WindowStyle Hidden
python engine/browser_engine.py estado
```

## Leer sin romper nada

```powershell
python engine/browser_engine.py js --expr "() => ({url: location.href, titulo: document.title})"
python engine/browser_engine.py js --expr "() => Array.from(document.querySelectorAll('a')).map(a => a.href).slice(0,20)"
```

## Clic que sí registra

```powershell
python engine/browser_engine.py clic --selector "button.primary"
python engine/browser_engine.py clic --texto "Continuar"
```

Si el clic no hace nada, sospecha: (a) evento sintético, (b) elemento cubierto, (c) iframe.

## Inspeccionar un formulario antes de automatizarlo

```powershell
python engine/browser_engine.py js --expr "() => Array.from(document.querySelectorAll('input,textarea,select,[contenteditable=true]')).filter(e=>e.offsetWidth).map(e=>({tag:e.tagName,type:e.type,name:e.name,id:e.id,ph:e.getAttribute('placeholder')}))"
```

## Escribir en un editor enriquecido (TinyMCE / Atto)

```powershell
python engine/browser_engine.py js --expr "() => { tinymce.activeEditor.setContent('<p>Hola</p>'); tinymce.activeEditor.save(); return tinymce.activeEditor.getContent().length; }"
```

## Captura y PDF con sesión

```powershell
python engine/browser_engine.py shot --salida "evidencia\pagina.png" --full
python engine/browser_engine.py pdf  --salida "evidencia\pagina.pdf"
```

PDF en navegador visible = CDP `Page.printToPDF` (ver `cmd_pdf`).

## Subir un archivo

```powershell
python engine/browser_engine.py clic --selector ".fp-btn-add a"
python engine/browser_engine.py js --expr "() => document.querySelectorAll('input[type=file]').length"
# con Playwright directo: set_input_files(ruta) y confirmar
```

## Autenticarse por portal y entrar a un host

```powershell
python engine/browser_engine.py clic --texto "Mis cursos"
python engine/browser_engine.py js --expr "() => { /* la funcion del portal que abre el curso */ }"
python engine/browser_engine.py tabs --limpiar
```

## Diagnóstico cuando «se cerró»

1. `estado` → ¿servidor vivo? ¿pestañas?
2. `serve.log` → ¿excepción? ¿sesión vencida?
3. ¿Se mató el proceso desde fuera? Busca `Stop-Process` en el historial.
4. ¿El perfil estaba en uso por otra ventana? Mensaje `ProcessSingleton`.

## Anti-patrones

- Abrir un navegador nuevo para cada consulta.
- `Stop-Process` sobre el perfil para «liberar»: destruye todas las sesiones.
- Comparar pestañas por URL.
- Escribir en el DOM de un editor enriquecido.
- Reportar éxito sin reabrir el artefacto.
