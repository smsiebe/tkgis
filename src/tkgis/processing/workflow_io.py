"""Save and load workflow definitions as YAML files.

Uses grdl-runtime's :class:`WorkflowDefinition` serialization when
available; falls back to plain dict round-tripping otherwise.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

try:
    import grdl_rt
except ImportError:  # pragma: no cover
    grdl_rt = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def save_workflow(workflow_steps: list[dict[str, Any]], path: str | Path) -> None:
    """Persist *workflow_steps* to a YAML file at *path*.

    Each element in *workflow_steps* is a dict with at least
    ``processor_name`` and optional ``params``.  The list is wrapped in a
    grdl-runtime ``WorkflowDefinition`` envelope so it can be loaded by
    either tkgis or grdl-runtime's ``load_workflow()``.

    Parameters
    ----------
    workflow_steps:
        Ordered list of step dicts, e.g.
        ``[{"processor_name": "Median", "params": {"kernel": 3}}]``.
    path:
        Destination file path (should end with ``.yaml`` or ``.yml``).
    """
    path = Path(path)

    if grdl_rt is not None:
        steps = []
        for s in workflow_steps:
            step = grdl_rt.ProcessingStep(
                processor_name=s["processor_name"],
                params=s.get("params", {}),
            )
            steps.append(step)
        wd = grdl_rt.WorkflowDefinition(
            name=path.stem,
            steps=steps,
        )
        data = wd.to_dict()
    else:
        # Minimal fallback format compatible with grdl-runtime
        data = {
            "name": path.stem,
            "version": "0.1.0",
            "schema_version": "3.0",
            "steps": workflow_steps,
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=False)

    logger.info("Workflow saved to %s", path)


def load_workflow(path: str | Path) -> list[dict[str, Any]]:
    """Load a workflow YAML and return the list of step dicts.

    Parameters
    ----------
    path:
        Source YAML file.

    Returns
    -------
    list[dict]
        Each dict has ``processor_name`` and ``params`` keys.
    """
    path = Path(path)

    if grdl_rt is not None:
        wd = grdl_rt.load_workflow(str(path))
        # topological_sort() returns [[step_id, ...], ...] grouped by level.
        # Flatten and resolve each step via get_step().
        steps: list[dict[str, Any]] = []
        for level in wd.topological_sort():
            for step_id in level:
                s = wd.get_step(step_id)
                steps.append({
                    "processor_name": s.processor_name,
                    "params": dict(s.params) if s.params else {},
                })
        return steps

    # Fallback: raw YAML parse
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    raw_steps = data.get("steps", [])
    return [
        {
            "processor_name": s.get("processor_name", s.get("name", "")),
            "params": s.get("params", {}),
        }
        for s in raw_steps
    ]
