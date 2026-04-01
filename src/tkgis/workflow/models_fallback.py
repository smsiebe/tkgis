"""Fallback models for the visual workflow builder when grdl-runtime is unavailable."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FallbackNodeInfo:
    """Lightweight stand-in for ``grdl_rt.execution.graph.NodeInfo``."""

    step_id: str = ""
    processor_name: str = ""
    processor_version: str | None = None
    display_name: str = ""
    category: str | None = None
    input_type: str | None = None
    output_type: str | None = None
    output_ports: dict[str, str] | None = None
    params: dict[str, Any] = field(default_factory=dict)
    param_specs: dict[str, dict] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    phase: str | None = None
    position: tuple[float, float] | None = None


@dataclass
class _FallbackEdgeInfo:
    """Lightweight stand-in for ``grdl_rt.execution.graph.EdgeInfo``."""

    source_id: str = ""
    source_port: str | None = None
    target_id: str = ""
    target_port: str | None = None
    data_type: str | None = None


class FallbackGraph:
    """Minimal local graph when grdl-runtime is unavailable.

    Provides the same CRUD API as ``WorkflowGraph`` so the canvas, tests,
    and connection validator can operate without a runtime dependency.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, _FallbackNodeInfo] = {}
        self._edges: list[_FallbackEdgeInfo] = []
        self._counter = 0

    def get_nodes(self) -> list[_FallbackNodeInfo]:
        return list(self._nodes.values())

    def get_edges(self) -> list[_FallbackEdgeInfo]:
        return list(self._edges)

    def get_node(self, step_id: str) -> _FallbackNodeInfo | None:
        return self._nodes.get(step_id)

    def add_node(
        self,
        processor_name: str,
        params: dict[str, Any] | None = None,
        position: tuple[float, float] | None = None,
        *,
        input_type: str | None = None,
        output_type: str | None = None,
    ) -> str:
        step_id = f"step_{self._counter}"
        self._counter += 1
        display = processor_name.rsplit(".", 1)[-1]
        self._nodes[step_id] = _FallbackNodeInfo(
            step_id=step_id,
            processor_name=processor_name,
            display_name=display,
            input_type=input_type,
            output_type=output_type,
            params=params or {},
            position=position,
        )
        return step_id

    def remove_node(self, step_id: str) -> None:
        if step_id not in self._nodes:
            raise KeyError(f"No node with id '{step_id}'")
        del self._nodes[step_id]
        self._edges = [
            e
            for e in self._edges
            if e.source_id != step_id and e.target_id != step_id
        ]
        for node in self._nodes.values():
            node.depends_on = [d for d in node.depends_on if d != step_id]

    def connect(
        self,
        source_id: str,
        target_id: str,
        source_port: str | None = None,
        target_port: str | None = None,
    ) -> None:
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)
        if source is None:
            raise KeyError(f"No node with id '{source_id}'")
        if target is None:
            raise KeyError(f"No node with id '{target_id}'")
        if source_id not in target.depends_on:
            target.depends_on.append(source_id)
        self._edges.append(
            _FallbackEdgeInfo(
                source_id=source_id,
                source_port=source_port,
                target_id=target_id,
                target_port=target_port,
                data_type=source.output_type,
            )
        )

    def disconnect(self, source_id: str, target_id: str) -> None:
        target = self._nodes.get(target_id)
        if target is not None:
            target.depends_on = [d for d in target.depends_on if d != source_id]
        self._edges = [
            e
            for e in self._edges
            if not (e.source_id == source_id and e.target_id == target_id)
        ]

    def update_node_params(self, step_id: str, params: dict) -> None:
        node = self._nodes.get(step_id)
        if node is None:
            raise KeyError(f"No node with id '{step_id}'")
        node.params.update(params)

    def update_node_position(
        self, step_id: str, position: tuple[float, float]
    ) -> None:
        node = self._nodes.get(step_id)
        if node is None:
            raise KeyError(f"No node with id '{step_id}'")
        node.position = position

    def validate(self) -> list[str]:
        errors: list[str] = []
        for edge in self._edges:
            src = self._nodes.get(edge.source_id)
            tgt = self._nodes.get(edge.target_id)
            if src is None:
                errors.append(f"Missing source node '{edge.source_id}'")
            if tgt is None:
                errors.append(f"Missing target node '{edge.target_id}'")
            if src and tgt:
                if (
                    src.output_type is not None
                    and tgt.input_type is not None
                    and src.output_type != tgt.input_type
                ):
                    errors.append(
                        f"Type mismatch: {edge.source_id} outputs "
                        f"'{src.output_type}' but {edge.target_id} "
                        f"expects '{tgt.input_type}'"
                    )
        return errors

    def topological_levels(self) -> list[list[str]]:
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        children: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges:
            if edge.target_id in in_degree:
                in_degree[edge.target_id] += 1
            if edge.source_id in children:
                children[edge.source_id].append(edge.target_id)

        levels: list[list[str]] = []
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        while queue:
            levels.append(sorted(queue))
            next_queue: list[str] = []
            for nid in queue:
                for child in children.get(nid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue
        return levels
