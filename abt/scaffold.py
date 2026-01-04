from __future__ import annotations

from pathlib import Path


def scaffold_project(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "agents").mkdir(exist_ok=True)
    (target / "skills" / "refund_policy").mkdir(parents=True, exist_ok=True)
    (target / "tools").mkdir(exist_ok=True)
    (target / "macros").mkdir(exist_ok=True)

    _write_if_missing(
        target / "macros" / "output_json.md",
        "Return responses in JSON with keys: \"answer\" and \"next_step\".\n",
    )
    _write_if_missing(
        target / "skills" / "refund_policy" / "SKILL.md",
        "If the user requests a refund, provide the official policy:\n"
        "We offer refunds within 30 days of purchase with proof of receipt.\n",
    )
    _write_if_missing(
        target / "agents" / "support_agent.md",
        "---\n"
        "name: support_agent\n"
        "model_provider: openai\n"
        "temperature: 0.2\n"
        "---\n\n"
        "You are the support agent. Use the refund policy when asked about refunds.\n\n"
        "{{ ref(\"skills/refund_policy\") }}\n\n"
        "{{ ref(\"macros/output_json\") }}\n",
    )


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
