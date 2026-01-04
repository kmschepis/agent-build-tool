from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .utils import Frontmatter, now_iso, parse_frontmatter, read_text


class CompilationError(Exception):
    pass


@dataclass
class AgentArtifact:
    name: str
    metadata: dict[str, Any]
    system_prompt: str
    dependencies: list[str] = field(default_factory=list)


class RefResolver:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.stack: list[Path] = []
        self.dependencies: list[str] = []

    def resolve(self, ref_path: str) -> str:
        normalized = ref_path.strip()
        if not normalized:
            raise CompilationError("ref() was called with an empty path")
        path = self._resolve_path(normalized)
        if path in self.stack:
            cycle = " -> ".join(str(p.relative_to(self.root)) for p in self.stack + [path])
            raise CompilationError(f"Cyclic ref detected: {cycle}")
        self.stack.append(path)
        try:
            content = read_text(path)
            self.dependencies.append(self._format_dependency(path))
            rendered = self._render_nested(content)
        finally:
            self.stack.pop()
        return rendered

    def _resolve_path(self, ref_path: str) -> Path:
        candidate = self.root / ref_path
        if candidate.is_dir():
            skill_file = candidate / "SKILL.md"
            if skill_file.exists():
                return skill_file
        if candidate.exists():
            return candidate
        if candidate.suffix == "":
            md_candidate = candidate.with_suffix(".md")
            if md_candidate.exists():
                return md_candidate
        raise CompilationError(f"ref() could not find '{ref_path}'")

    def _format_dependency(self, path: Path) -> str:
        return str(path.relative_to(self.root))

    def _render_nested(self, content: str) -> str:
        from jinja2 import Environment, StrictUndefined

        env = Environment(undefined=StrictUndefined)
        env.globals["ref"] = self.resolve
        template = env.from_string(content)
        return template.render()


def _render_agent(env: Environment, resolver: RefResolver, frontmatter: Frontmatter) -> str:
    env.globals["ref"] = resolver.resolve
    template = env.from_string(frontmatter.body)
    return template.render()


def compile_project(root: Path) -> dict[str, Any]:
    agents_dir = root / "agents"
    if not agents_dir.exists():
        raise CompilationError("agents/ directory not found")

    from jinja2 import Environment, StrictUndefined

    env = Environment(undefined=StrictUndefined)
    manifest: dict[str, Any] = {
        "compiled_at": now_iso(),
        "agents": {},
    }

    for agent_file in sorted(agents_dir.glob("*.md")):
        content = read_text(agent_file)
        frontmatter = parse_frontmatter(content)
        metadata = dict(frontmatter.metadata)
        name = metadata.get("name") or agent_file.stem
        resolver = RefResolver(root)
        system_prompt = _render_agent(env, resolver, frontmatter)
        artifact = AgentArtifact(
            name=name,
            metadata=metadata,
            system_prompt=system_prompt.strip(),
            dependencies=resolver.dependencies,
        )
        manifest["agents"][name] = {
            "model_provider": metadata.get("model_provider"),
            "temperature": metadata.get("temperature"),
            "system_prompt": artifact.system_prompt,
            "dependencies": artifact.dependencies,
        }

    return manifest
