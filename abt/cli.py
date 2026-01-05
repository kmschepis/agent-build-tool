from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import CompilationError, compile_project
from .docs import generate_docs
from .runtime import run_server
from .scaffold import scaffold_project
from .utils import write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abt", description="Agent Build Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Scaffold a new ABT project")
    init_parser.add_argument("path", nargs="?", default=".", help="Target directory")

    compile_parser = subparsers.add_parser("compile", help="Compile ABT project to manifest")
    compile_parser.add_argument(
        "--output",
        default="abt_manifest.json",
        help="Output manifest path",
    )

    docs_parser = subparsers.add_parser("docs", help="Generate ABT docs")
    docs_parser.add_argument(
        "--output",
        default=None,
        help="Output directory (defaults to abt_docs)",
    )

    run_parser = subparsers.add_parser("run", help="Run local chat runtime")
    run_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface for the local server",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for the local server",
    )

    args = parser.parse_args(argv)

    if args.command == "init":
        target = Path(args.path).resolve()
        scaffold_project(target)
        print(f"Initialized ABT project at {target}")
        return 0

    root = Path.cwd()

    if args.command == "compile":
        try:
            manifest = compile_project(root)
        except CompilationError as exc:
            print(f"Compilation failed: {exc}")
            return 1
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = root / output_path
        write_json(output_path, manifest)
        print(f"Wrote manifest to {output_path}")
        return 0

    if args.command == "docs":
        output_dir = Path(args.output) if args.output else None
        try:
            html_path = generate_docs(root, output_dir=output_dir)
        except CompilationError as exc:
            print(f"Docs generation failed: {exc}")
            return 1
        print(f"Generated docs at {html_path}")
        return 0

    if args.command == "run":
        try:
            run_server(root, host=args.host, port=args.port)
        except CompilationError as exc:
            print(f"Runtime startup failed: {exc}")
            return 1
        return 0

    parser.print_help()
    return 1
