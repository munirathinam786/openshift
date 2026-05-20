from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel

from .agent import OpenShiftSreAgent
from .config import Settings

app = typer.Typer(help="OpenShift SRE local-model agent")
console = Console()


@app.command()
def ask(prompt: str, show_steps: bool = typer.Option(True, help="Show the reasoning/tool trace.")) -> None:
    """Ask the agent to investigate an OpenShift SRE question."""
    agent = OpenShiftSreAgent(Settings.load())
    result = agent.ask(prompt)
    console.print(Panel.fit(result.answer, title="OpenShift SRE Agent"))
    if show_steps:
        console.print_json(json.dumps(result.steps, default=str))


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP API that can be containerized or called from other tools."""
    import uvicorn

    uvicorn.run("openshift_sre_agent.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
