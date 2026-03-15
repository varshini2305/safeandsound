from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swaybench.eval.heuristics import concession_score, resistance_score, stance_change_score


def _dataset_path() -> Path:
    p = os.environ.get("SWAYBENCH_DATASET", "")
    if p:
        return Path(p)
    return Path("swaybench.jsonl")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(__import__("json").loads(line))
    return rows


def _inspect_available() -> bool:
    try:
        import inspect_ai  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


if _inspect_available():
    from inspect_ai.dataset import Sample  # type: ignore
    from inspect_ai.model import ChatMessageUser  # type: ignore
    from inspect_ai.scorer import Score, Scorer, scorer  # type: ignore
    from inspect_ai.solver import Solver, generate, solver  # type: ignore
    from inspect_ai.task import Task, task  # type: ignore

    @solver
    def two_step_pushback() -> Solver:
        async def solve(state, generate_fn=generate):
            question = state.input
            challenge = state.metadata.get("user_challenge", "")
            state.messages.append(ChatMessageUser(content=str(question)))
            await generate_fn(state)
            m1 = state.output.completion
            state.store["m1"] = m1
            state.messages.append(ChatMessageUser(content=str(challenge)))
            await generate_fn(state)
            return state

        return solve

    @scorer(metrics={"concession": ["mean"], "stance_change": ["mean"], "resistance": ["mean"]})
    def sway_scorer() -> Scorer:
        async def score(state, target) -> Score:
            m1 = state.store.get("m1", "") or ""
            m2 = state.output.completion or ""
            return Score(
                value={
                    "concession": float(concession_score(m2)),
                    "stance_change": float(stance_change_score(m1, m2)),
                    "resistance": float(resistance_score(m2)),
                }
            )

        return score

    @task
    def swaybench_flip_under_pushback() -> Task:
        path = _dataset_path()
        rows = _load_jsonl(path)
        samples = []
        for r in rows:
            samples.append(
                Sample(
                    input=r.get("user_question", ""),
                    metadata={
                        "user_challenge": r.get("user_challenge", ""),
                    },
                )
            )
        return Task(
            dataset=samples,
            solver=two_step_pushback(),
            scorer=sway_scorer(),
        )

