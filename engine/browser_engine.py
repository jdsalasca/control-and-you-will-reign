"""browser_engine — un navegador real, una sola sesión, muchos comandos.

Problema que resuelve: automatizar un sitio con sesión iniciada sin perder la
sesión cada vez. Playwright puede lanzar un Chrome persistente, pero solo el
proceso que lo lanzó puede controlarlo: un segundo `connect_over_cdp` se cuelga.

Solución: un proceso `serve` que posee el navegador y una cola de trabajos en
disco. Cualquier otro comando deja un `.job`, el servidor lo ejecuta con el
contexto vivo y devuelve la salida por `.out`.

Uso:
    python browser_engine.py serve --url https://ejemplo.com
    python browser_engine.py estado
    python browser_engine.py abrir https://ejemplo.com/pagina
    python browser_engine.py js --expr "() => document.title"
    python browser_engine.py clic --selector "button.primary"
    python browser_engine.py clic --texto "Continuar"
    python browser_engine.py shot --salida captura.png
    python browser_engine.py pdf --salida pagina.pdf
    python browser_engine.py tabs --limpiar
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

PERFIL = os.environ.get("BROWSER_PROFILE", str(Path.home() / ".browser-engine-profile"))
PUERTO = os.environ.get("BROWSER_PORT", "9223")
JOBS = Path(
    os.environ.get("BROWSER_JOBS", str(Path(tempfile.gettempdir()) / "browser_engine"))
)
ALIVE = JOBS / "alive"
CTX = None


# --------------------------------------------------------------------------- utilidades


def _marcar_vivo() -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    ALIVE.write_text(str(os.getpid()), encoding="utf-8")


def _servidor_arriba() -> bool:
    try:
        return (time.time() - ALIVE.stat().st_mtime) < 15
    except OSError:
        return False


def _pagina(ctx):
    """Reutiliza una pestaña existente; nunca abre una nueva por consulta."""
    return ctx.pages[0] if ctx.pages else ctx.new_page()


@contextlib.contextmanager
def sesion():
    global CTX
    if CTX is not None:
        yield CTX
        return
    with sync_playwright() as p:
        yield p.chromium.connect_over_cdp(f"http://127.0.0.1:{PUERTO}").contexts[0]


def _limpiar_pestanas(ctx) -> int:
    """Cierra solo about:blank y duplicadas. Nunca la pestaña de trabajo."""
    cerradas, vistas = 0, set()
    for pg in list(ctx.pages):
        try:
            url = pg.url
        except Exception:  # noqa: BLE001
            continue
        if url in ("about:blank", ""):
            pg.close()
            cerradas += 1
            continue
        if url in vistas and len(ctx.pages) > 2:
            pg.close()
            cerradas += 1
            continue
        vistas.add(url)
    return cerradas


# --------------------------------------------------------------------------- servidor


def _procesar_trabajos() -> None:
    for job in sorted(JOBS.glob("*.job")):
        destino = job.with_suffix(".out")
        buf = io.StringIO()
        try:
            argv = json.loads(job.read_text(encoding="utf-8"))
            args = _parser().parse_args(argv)
            with contextlib.redirect_stdout(buf):
                args.func(args)
        except SystemExit:
            buf.write("argumentos invalidos\n")
        except Exception as e:  # noqa: BLE001
            buf.write(f"ERROR: {type(e).__name__}: {e}\n")
        finally:
            job.unlink(missing_ok=True)
        destino.write_text(buf.getvalue(), encoding="utf-8")


def cmd_serve(args) -> int:
    global CTX
    if _servidor_arriba():
        print("ya hay un serve vivo; usa 'estado'")
        return 0
    perfil = Path(args.perfil)
    perfil.mkdir(parents=True, exist_ok=True)
    _marcar_vivo()
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(perfil),
                channel=args.canal,
                headless=False,
                no_viewport=True,
                args=[
                    f"--remote-debugging-port={args.puerto}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )
            CTX = ctx
            print(f"NAVEGADOR LISTO puerto {args.puerto} perfil {perfil}", flush=True)
            pg = _pagina(ctx)
            if args.url:
                try:
                    pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
                except Exception as e:  # noqa: BLE001
                    print("aviso: no se pudo abrir la url inicial:", str(e)[:80])
            ultimo = time.time()
            while True:
                _marcar_vivo()
                _procesar_trabajos()
                if args.ping and time.time() - ultimo >= args.ping * 60:
                    ultimo = time.time()
                    try:
                        ctx.request.get(
                            args.ping_url or args.url or "about:blank", timeout=60000
                        )
                    except Exception as e:  # noqa: BLE001
                        print(
                            time.strftime("%H:%M:%S"),
                            "ping error:",
                            str(e)[:80],
                            flush=True,
                        )
                time.sleep(0.5)
    except Exception as e:  # noqa: BLE001
        if "ProcessSingleton" in str(e) or "already in use" in str(e):
            print("El perfil esta en uso por otra ventana. Cierrala y reintenta.")
            return 2
        raise
    finally:
        ALIVE.unlink(missing_ok=True)
    return 0


def _encolar_y_esperar(argv: list[str], espera: int = 300) -> int:
    JOBS.mkdir(parents=True, exist_ok=True)
    jid = uuid.uuid4().hex[:12]
    job, out = JOBS / f"{jid}.job", JOBS / f"{jid}.out"
    job.write_text(json.dumps(argv, ensure_ascii=False), encoding="utf-8")
    fin = time.time() + espera
    while time.time() < fin:
        if out.exists():
            print(out.read_text(encoding="utf-8"), end="")
            out.unlink(missing_ok=True)
            return 0
        time.sleep(0.4)
    print("sin respuesta del serve")
    return 1


# --------------------------------------------------------------------------- comandos


def cmd_estado(args) -> int:
    print("servidor:", "vivo" if _servidor_arriba() else "apagado")
    with sesion() as ctx:
        print("pestañas:", len(ctx.pages))
        for pg in ctx.pages[:12]:
            try:
                print("  -", pg.title()[:60], "|", pg.url[:90])
            except Exception:  # noqa: BLE001
                pass
    return 0


def cmd_abrir(args) -> int:
    with sesion() as ctx:
        pg = ctx.new_page()
        pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(1500)
        print("titulo:", pg.title())
        print("url:", pg.url)
    return 0


def cmd_js(args) -> int:
    with sesion() as ctx:
        pg = _pagina(ctx)
        if args.url:
            pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(args.espera)
        resultado = pg.evaluate(args.expr)
        texto = json.dumps(resultado, ensure_ascii=False, indent=1)
        print(texto[:8000])
        if args.salida:
            Path(args.salida).write_text(texto, encoding="utf-8")
    return 0


def cmd_clic(args) -> int:
    with sesion() as ctx:
        pg = _pagina(ctx)
        if args.url:
            pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(args.espera)
        if args.selector:
            pg.locator(args.selector).first.click(force=True, timeout=10000)
            print("clic:", args.selector)
        elif args.texto:
            objetivo = pg.get_by_text(args.texto, exact=True)
            for i in range(objetivo.count()):
                el = objetivo.nth(i)
                if el.is_visible():
                    el.click(force=True, timeout=10000)
                    print("clic:", args.texto)
                    break
        else:
            print("falta --selector o --texto")
            return 1
        pg.wait_for_timeout(args.pausa)
    return 0


def cmd_shot(args) -> int:
    with sesion() as ctx:
        pg = _pagina(ctx)
        if args.url:
            pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(args.espera)
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(destino), full_page=args.full)
        print("guardado:", destino)
    return 0


def cmd_pdf(args) -> int:
    with sesion() as ctx:
        pg = _pagina(ctx)
        if args.url:
            pg.goto(args.url, wait_until="domcontentloaded", timeout=90000)
            pg.wait_for_timeout(args.espera)
        cdp = ctx.new_cdp_session(pg)
        datos = cdp.send(
            "Page.printToPDF",
            {"printBackground": True, "preferCSSPageSize": True},
        )
        destino = Path(args.salida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(base64.b64decode(datos["data"]))
        print("guardado:", destino, destino.stat().st_size, "bytes")
    return 0


def cmd_tabs(args) -> int:
    with sesion() as ctx:
        antes = len(ctx.pages)
        cerradas = _limpiar_pestanas(ctx) if args.limpiar else 0
        print(f"pestañas: {antes} -> {len(ctx.pages)} (cerradas {cerradas})")
        for pg in ctx.pages[:15]:
            print("  -", pg.url[:100])
    return 0


# --------------------------------------------------------------------------- parser


def _parser():
    ap = argparse.ArgumentParser(
        description="Navegador persistente con cola de trabajos"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="lanza el navegador y atiende trabajos")
    s.add_argument("--perfil", default=PERFIL)
    s.add_argument("--puerto", default=PUERTO)
    s.add_argument("--canal", default="chrome")
    s.add_argument("--url", default="")
    s.add_argument("--ping", type=int, default=15, help="minutos entre pings")
    s.add_argument("--ping-url", default="")
    s.set_defaults(func=cmd_serve)

    sub.add_parser("estado", help="servidor, pestañas").set_defaults(func=cmd_estado)

    a = sub.add_parser("abrir", help="abre una pestaña")
    a.add_argument("url")
    a.set_defaults(func=cmd_abrir)

    j = sub.add_parser("js", help="evalua JavaScript y devuelve JSON")
    j.add_argument("--expr", required=True)
    j.add_argument("--url")
    j.add_argument("--espera", type=int, default=2500)
    j.add_argument("--salida")
    j.set_defaults(func=cmd_js)

    c = sub.add_parser("clic", help="clic real por selector o texto")
    c.add_argument("--selector")
    c.add_argument("--texto")
    c.add_argument("--url")
    c.add_argument("--espera", type=int, default=2500)
    c.add_argument("--pausa", type=int, default=1500)
    c.set_defaults(func=cmd_clic)

    sh = sub.add_parser("shot", help="captura de pantalla")
    sh.add_argument("--salida", required=True)
    sh.add_argument("--url")
    sh.add_argument("--espera", type=int, default=2500)
    sh.add_argument("--full", action="store_true")
    sh.set_defaults(func=cmd_shot)

    pf = sub.add_parser("pdf", help="guarda la pagina como PDF")
    pf.add_argument("--salida", required=True)
    pf.add_argument("--url")
    pf.add_argument("--espera", type=int, default=3000)
    pf.set_defaults(func=cmd_pdf)

    t = sub.add_parser("tabs", help="lista y limpia pestañas")
    t.add_argument("--limpiar", action="store_true")
    t.set_defaults(func=cmd_tabs)

    return ap


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args()
    if args.cmd != "serve" and _servidor_arriba():
        return _encolar_y_esperar(sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
