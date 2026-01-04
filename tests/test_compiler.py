import importlib.util
import tempfile
from pathlib import Path
import unittest

from abt.compiler import CompilationError, compile_project
from abt.scaffold import scaffold_project
from abt.utils import parse_frontmatter

HAS_JINJA = importlib.util.find_spec("jinja2") is not None
HAS_YAML = importlib.util.find_spec("yaml") is not None


class CompilerTests(unittest.TestCase):
    @unittest.skipIf(not HAS_YAML, "PyYAML not installed")
    def test_parse_frontmatter(self) -> None:
        content = """---\nname: demo\nmodel_provider: openai\n---\nHello\n"""
        parsed = parse_frontmatter(content)
        self.assertEqual(parsed.metadata["name"], "demo")
        self.assertIn("Hello", parsed.body)

    @unittest.skipIf(not (HAS_JINJA and HAS_YAML), "jinja2 or PyYAML not installed")
    def test_compile_project_from_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scaffold_project(root)
            manifest = compile_project(root)
            self.assertIn("support_agent", manifest["agents"])
            agent = manifest["agents"]["support_agent"]
            self.assertIn("refunds", agent["system_prompt"].lower())
            self.assertTrue(agent["dependencies"])

    @unittest.skipIf(not (HAS_JINJA and HAS_YAML), "jinja2 or PyYAML not installed")
    def test_cycle_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "agents").mkdir()
            (root / "macros").mkdir()
            (root / "macros" / "a.md").write_text("{{ ref('macros/b') }}", encoding="utf-8")
            (root / "macros" / "b.md").write_text("{{ ref('macros/a') }}", encoding="utf-8")
            (root / "agents" / "agent.md").write_text(
                "---\nname: loop\n---\n{{ ref('macros/a') }}\n", encoding="utf-8"
            )
            with self.assertRaises(CompilationError):
                compile_project(root)


if __name__ == "__main__":
    unittest.main()
