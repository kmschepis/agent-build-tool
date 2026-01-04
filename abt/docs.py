from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compiler import compile_project


def generate_docs(root: Path, output_dir: Path | None = None) -> Path:
    manifest = compile_project(root)
    output_dir = output_dir or (root / "abt_docs")
    output_dir.mkdir(parents=True, exist_ok=True)

    lineage_path = output_dir / "lineage.json"
    lineage_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    html_path = output_dir / "index.html"
    html_path.write_text(_render_html(manifest), encoding="utf-8")
    return html_path


def _render_html(manifest: dict[str, Any]) -> str:
    agent_rows = []
    agents = manifest.get("agents", {})
    for name, agent in agents.items():
        deps = agent.get("dependencies") or []
        dep_list = "".join(f"<li>{dep}</li>" for dep in deps) or "<li>No dependencies</li>"
        agent_rows.append(
            """
            <section class="card">
              <h2>{name}</h2>
              <p><strong>Model Provider:</strong> {provider}</p>
              <p><strong>Temperature:</strong> {temperature}</p>
              <h3>Dependencies</h3>
              <ul>{dep_list}</ul>
            </section>
            """.format(
                name=name,
                provider=agent.get("model_provider") or "unknown",
                temperature=agent.get("temperature") if agent.get("temperature") is not None else "default",
                dep_list=dep_list,
            )
        )

    return """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>ABT Docs</title>
      <style>
        body {{ font-family: Arial, sans-serif; background: #f7f7f9; margin: 0; padding: 2rem; }}
        h1 {{ margin-bottom: 1rem; }}
        .grid {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
        .card {{ background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
        ul {{ padding-left: 1.2rem; }}
      </style>
    </head>
    <body>
      <h1>Agent Build Tool Lineage</h1>
      <p>Generated documentation for compiled agents and their dependencies.</p>
      <div class="grid">{rows}</div>
    </body>
    </html>
    """.format(rows="\n".join(agent_rows))
