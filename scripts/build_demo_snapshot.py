from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from auditable_financial_agents.cli import load_case  # noqa: E402
from auditable_financial_agents.core import evaluate_case  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_utf8_lf(path: Path, text: str) -> None:
    """Write deterministic UTF-8 text regardless of the host platform."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    rows = []
    for path in sorted((ROOT / "examples").glob("*.json")):
        result = evaluate_case(load_case(path))
        rows.append(
            {
                "example": path.name,
                "case_id": result.case_id,
                "opinion": result.opinion,
                "human_review_required": result.human_review_required,
                "evidence_sufficiency": round(result.evidence_sufficiency, 6),
                "pervasiveness": round(result.pervasiveness, 6),
                "max_effective_severity": round(result.max_effective_severity, 6),
                "trace_completeness": round(result.trace_assessment.trace_completeness, 6),
                "task_completeness": result.trace_assessment.task_completeness,
                "completeness_basis": result.trace_assessment.completeness_basis,
            }
        )
    json_path = out_dir / "demo_results.json"
    write_utf8_lf(json_path, json.dumps(rows, indent=2) + "\n")

    lines = [
        "# Demo results",
        "",
        "These are deterministic **synthetic/public-safe examples**. They are not the HCOMP empirical results.",
        "",
        "| Example | Opinion | Human review | Evidence sufficiency | Pervasiveness | "
        "Max severity | Action-doc coverage | Task completeness |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['example']}` | {row['opinion']} | {str(row['human_review_required']).lower()} | "
            f"{row['evidence_sufficiency']:.3f} | {row['pervasiveness']:.3f} | "
            f"{row['max_effective_severity']:.3f} | {row['trace_completeness']:.3f} | "
            f"{row['task_completeness'] if row['task_completeness'] is not None else 'not assessed'} |"
        )
    md_path = out_dir / "DEMO_RESULTS.md"
    write_utf8_lf(md_path, "\n".join(lines) + "\n")

    manifest = {
        "kind": "synthetic_demo_snapshot",
        "artifacts": {
            json_path.relative_to(ROOT).as_posix(): sha256(json_path),
            md_path.relative_to(ROOT).as_posix(): sha256(md_path),
        },
        "examples": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in sorted((ROOT / "examples").glob("*.json"))
        },
    }
    manifest_path = out_dir / "DEMO_MANIFEST.json"
    write_utf8_lf(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {json_path.relative_to(ROOT)}")
    print(f"wrote {md_path.relative_to(ROOT)}")
    print(f"wrote {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
