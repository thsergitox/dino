"""`dino auth` — change the OpenAI API key without re-running the full setup.

Loads ~/.config/dino/config.toml, replaces only [whisper].api_key, and writes
the canonical file back. All other settings (model, language, prompt, timeout,
tui section, output adapter) are preserved.

Heavy imports (rich) live inside `run()` so `dino start` / `stop` / `toggle`
stay fast on every keypress.
"""

from __future__ import annotations

from dino import __version__, config_writer


def run() -> int:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt

    console = Console()

    console.print(
        Panel.fit(
            f"[bold cyan]dino auth[/bold cyan] [dim]v{__version__}[/dim]\n"
            "Cambiar la API key del proveedor STT.",
            border_style="cyan",
        )
    )
    console.print()

    path = config_writer.config_path()
    if not path.is_file():
        console.print(
            f"[red]No hay config existente en {path}.[/red]\n"
            "Corré [bold]dino setup[/bold] primero para hacer la configuración inicial."
        )
        return 1

    existing = config_writer.load_dict()
    whisper = existing.get("whisper", {})
    tui = existing.get("tui", {})
    output = existing.get("output", {})

    current = whisper.get("api_key", "")
    if current:
        masked = f"{current[:7]}…{current[-4:]}" if len(current) > 12 else "***"
        console.print(f"API key actual: [dim]{masked}[/dim]")
    else:
        console.print("[yellow]No hay API key en el archivo (¿estás usando $OPENAI_API_KEY?).[/yellow]")
    console.print()

    new_key = Prompt.ask(
        "[bold]Nueva OpenAI API key[/bold] (oculto, Enter sin cambios cancela)",
        password=True,
        default="",
        show_default=False,
    ).strip()

    if not new_key:
        console.print("[yellow]Cancelado. Nada cambió.[/yellow]")
        return 0

    if not new_key.startswith("sk-"):
        console.print("[red]La key no parece válida (debe empezar con 'sk-'). Cancelado.[/red]")
        return 1

    if new_key == current:
        console.print("[yellow]Es la misma key que ya tenés. Nada cambió.[/yellow]")
        return 0

    config_writer.write(
        api_key=new_key,
        model=whisper.get("model", "whisper-1"),
        language=whisper.get("language"),
        prompt=whisper.get("prompt"),
        timeout_seconds=float(whisper.get("timeout_seconds", 30)),
        tui_language=tui.get("language", "es"),
        tui_lifecycle=tui.get("lifecycle", "exec-once"),
        tui_terminal=tui.get("terminal") or None,
        output_adapter=output.get("adapter", "wl-copy"),
    )

    console.print()
    console.print(f"[green]✓[/green] API key actualizada en [cyan]{path}[/cyan]")
    console.print(
        "[dim]Si dino estaba corriendo, cerralo y volvelo a abrir para que tome la key nueva.[/dim]"
    )
    return 0
