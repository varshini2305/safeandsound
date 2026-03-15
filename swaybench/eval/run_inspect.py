from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, help="Path to SwayBench JSONL")
    ap.add_argument("--model", required=True, help="Inspect model identifier")
    args = ap.parse_args()

    os.environ["SWAYBENCH_DATASET"] = str(Path(args.dataset).resolve())

    try:
        from inspect_ai import eval as inspect_eval  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(
            "Inspect AI not installed. Install with: pip install -r requirements-inspect.txt"
        ) from e

    # Import registers the task.
    from swaybench.eval.inspect_task import swaybench_flip_under_pushback

    result = inspect_eval(swaybench_flip_under_pushback(), model=args.model)

    # Best-effort JSON: Inspect result objects vary by version.
    out = {"model": args.model}
    if hasattr(result, "summary"):
        out["summary"] = getattr(result, "summary")
    if hasattr(result, "metrics"):
        out["metrics"] = getattr(result, "metrics")
    if hasattr(result, "scores"):
        out["scores"] = getattr(result, "scores")
    print(json.dumps(out, default=str))


if __name__ == "__main__":
    main()

