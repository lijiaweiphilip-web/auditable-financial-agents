from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from .core import evaluate_case
from .schema import ArtifactCase, InputValidationError


def load_case(path: Path) -> ArtifactCase:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return ArtifactCase.from_dict(payload)


def evaluate_path(path: Path, output: Path | None = None) -> dict[str, Any]:
    result = evaluate_case(load_case(path))
    payload = result.to_dict()
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return payload


def demo(example_dir: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for path in sorted(example_dir.glob("*.json")):
        result = evaluate_case(load_case(path)).to_dict()
        outputs.append(result)
        print(f"{path.name:40s} -> {result['opinion']:10s} review={result['human_review_required']}")
    return outputs


def validate_case_path(path: Path) -> int:
    try:
        load_case(path)
    except (InputValidationError, ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 2
    print("valid")
    return 0


def print_schema(name: str) -> int:
    names = {
        "artifact-case": "artifact_case.schema.json",
        "audit-result": "audit_result.schema.json",
        "trace-assessment": "trace_assessment.schema.json",
    }
    filename = names.get(name)
    if filename is None:
        print(f"invalid: unknown schema {name!r}", file=sys.stderr)
        return 2
    try:
        schema_path = resources.files("auditable_financial_agents.schemas").joinpath(filename)
        print(schema_path.read_text(encoding="utf-8"), end="")
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        print(f"invalid: packaged schema unavailable: {exc}", file=sys.stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="financial-agent-audit",
        description="Research-label audit certificates for synthetic financial-agent artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser("evaluate", help="evaluate one JSON case")
    evaluate.add_argument("case", type=Path)
    evaluate.add_argument("--output", type=Path)

    demo_cmd = sub.add_parser("demo", help="run all JSON examples")
    demo_cmd.add_argument("--examples", type=Path, default=Path("examples"))

    validate_cmd = sub.add_parser("validate-case", help="validate one JSON case without evaluating it")
    validate_cmd.add_argument("case", type=Path)
    schema_cmd = sub.add_parser("print-schema", help="print a packaged JSON Schema")
    schema_cmd.add_argument("name", choices=("artifact-case", "audit-result", "trace-assessment"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evaluate":
        evaluate_path(args.case, args.output)
        return 0
    if args.command == "demo":
        demo(args.examples)
        return 0
    if args.command == "validate-case":
        return validate_case_path(args.case)
    if args.command == "print-schema":
        return print_schema(args.name)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
