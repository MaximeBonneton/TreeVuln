"""
Inference engine for vulnerability evaluation.
"""

import logging
from typing import Any

from app.engine.nodes import BaseNode, NodeEvaluationError, OutputNode, create_node

logger = logging.getLogger(__name__)
from app.schemas.evaluation import DecisionPath, EvaluationResult
from app.schemas.tree import EdgeSchema, NodeSchema, NodeType, TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class InferenceEngine:
    """
    Inference engine that loads a tree and evaluates vulnerabilities.
    """

    def __init__(self, tree_structure: TreeStructure):
        self.tree_structure = tree_structure
        self.nodes: dict[str, BaseNode] = {}
        self.edges: dict[str, list[EdgeSchema]] = {}  # source_id -> [edges]
        self.root_node_id: str | None = None

        self._build_tree()

    def _build_tree(self) -> None:
        """Build the internal tree structure."""
        # Create nodes
        for node_schema in self.tree_structure.nodes:
            self.nodes[node_schema.id] = create_node(node_schema)

        # Indexe les edges par source
        for edge in self.tree_structure.edges:
            if edge.source not in self.edges:
                self.edges[edge.source] = []
            self.edges[edge.source].append(edge)

        # Find the root node (the one not targeted by any edge)
        target_nodes = {e.target for e in self.tree_structure.edges}
        for node_id in self.nodes:
            if node_id not in target_nodes:
                self.root_node_id = node_id
                break

        if self.root_node_id is None and self.nodes:
            # If no clear root, take the first INPUT or EQUATION node
            for node_id, node in self.nodes.items():
                if node.type in (NodeType.INPUT, NodeType.EQUATION):
                    self.root_node_id = node_id
                    break

    def evaluate(
        self,
        vulnerability: VulnerabilityInput,
        lookups: dict[str, dict[str, dict[str, Any]]] | None = None,
        include_path: bool = True,
    ) -> EvaluationResult:
        """
        Evaluate a vulnerability by traversing the tree.

        Args:
            vulnerability: The vulnerability to evaluate
            lookups: Pre-loaded lookup cache {table: {key: {field: value}}}
            include_path: If True, includes the decision path (audit trail)

        Returns:
            EvaluationResult with the decision and path
        """
        # Vulnerability identifier (id or cve_id as fallback)
        vuln_id = vulnerability.id or vulnerability.cve_id

        if not self.root_node_id:
            return EvaluationResult(
                vuln_id=vuln_id,
                decision="Error",
                error="Empty or invalid tree",
            )

        # Prepare the context
        context = {
            "vulnerability": vulnerability.model_dump(),
            "lookups": lookups or {},
        }

        path: list[DecisionPath] = []
        current_node_id = self.root_node_id
        current_input_index: int | None = None  # Track which input we entered through

        # Safety limit against infinite loops
        max_iterations = 100
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            node = self.nodes.get(current_node_id)
            if node is None:
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision="Error",
                    path=path if include_path else [],
                    error=f"Node {current_node_id} not found",
                )

            try:
                value, condition_label = node.evaluate(context)
            except NodeEvaluationError as e:
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision="Error",
                    path=path if include_path else [],
                    error=str(e),
                )

            # Enregistre le chemin
            if include_path:
                field_evaluated = None
                if hasattr(node, "config"):
                    if node.type == NodeType.EQUATION:
                        field_evaluated = node.config.get("formula")
                    else:
                        field_evaluated = node.config.get("field") or node.config.get("lookup_field")

                path.append(
                    DecisionPath(
                        node_id=node.id,
                        node_label=node.label,
                        node_type=node.type.value,
                        field_evaluated=field_evaluated,
                        value_found=value,
                        condition_matched=condition_label,
                    )
                )

            # If it is an OUTPUT node, we are done
            if isinstance(node, OutputNode):
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision=str(value),
                    decision_color=node.config.get("color"),
                    path=path if include_path else [],
                )

            # Find the index of the matched condition
            condition_index = None
            if condition_label and hasattr(node, "conditions"):
                for idx, cond in enumerate(node.conditions):
                    if cond.label == condition_label:
                        condition_index = idx
                        break

            # Check if this is a multi-input node
            input_count = node.config.get("input_count", 1) if hasattr(node, "config") else 1

            # Find the edge to follow based on the condition and input_index
            next_node_id, next_target_handle = self._find_next_node(
                current_node_id, condition_label, condition_index, current_input_index, input_count
            )
            if next_node_id is None:
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision="Error",
                    path=path if include_path else [],
                    error=f"No branch for condition '{condition_label}' of node {node.id}",
                )

            current_node_id = next_node_id
            # Parse the target_handle to get the input index for the next node
            current_input_index = self._parse_input_index(next_target_handle)

            # Validate that input_index is within bounds of target node
            if current_input_index is not None:
                next_node = self.nodes.get(current_node_id)
                if next_node and hasattr(next_node, "config"):
                    target_input_count = next_node.config.get("input_count", 1)
                    if current_input_index >= target_input_count:
                        return EvaluationResult(
                            vuln_id=vuln_id,
                            decision="Error",
                            path=path if include_path else [],
                            error=(
                                f"input_index={current_input_index} hors limites pour "
                                f"node '{current_node_id}' (input_count={target_input_count})"
                            ),
                        )

        return EvaluationResult(
            vuln_id=vuln_id,
            decision="Error",
            path=path if include_path else [],
            error="Iteration limit reached (infinite loop detected?)",
        )

    def _parse_input_index(self, target_handle: str | None) -> int | None:
        """Parse input index from target_handle (e.g., 'input-2' -> 2)."""
        if not target_handle:
            return None
        if target_handle.startswith("input-"):
            parts = target_handle.split("-")
            if len(parts) < 2:
                logger.warning("target_handle '%s' invalid: expected format 'input-{index}'", target_handle)
                return None
            try:
                return int(parts[1])
            except ValueError:
                logger.warning("target_handle '%s' invalid: '%s' is not an integer", target_handle, parts[1])
                return None
        return None

    def _find_next_node(
        self,
        source_id: str,
        condition_label: str | None,
        condition_index: int | None = None,
        input_index: int | None = None,
        input_count: int = 1,
    ) -> tuple[str | None, str | None]:
        """
        Find the next node based on the matched condition.

        For multi-input nodes (input_count > 1), the source_handle format is:
        'handle-{input_index}-{condition_index}'

        For single-input nodes, the format remains:
        'handle-{condition_index}'

        Returns:
            Tuple of (next_node_id, target_handle of the edge)
        """
        edges = self.edges.get(source_id, [])

        if not edges:
            return None, None

        # Si une seule edge ET qu'on ne connaît pas l'index de la condition
        # matchée (routage par défaut sans conditions, ex: LookupNode sans
        # clé trouvée), on peut la suivre sans risque. En revanche, si une
        # condition a été matchée (condition_index connu), ce raccourci ne
        # doit PAS être appliqué aveuglément : il faut vérifier que l'unique
        # edge correspond bien au bon handle, sinon aucune branche ne
        # correspond réellement (E-2).
        if len(edges) == 1 and condition_index is None:
            return edges[0].target, edges[0].target_handle

        # Build the expected source_handle based on input_count
        if condition_index is not None:
            if input_count > 1 and input_index is not None:
                # Multi-input mode: handle-{input}-{condition}
                handle_id = f"handle-{input_index}-{condition_index}"
            else:
                # Single-input mode: handle-{condition}
                handle_id = f"handle-{condition_index}"

            # Search for edge with matching source_handle
            for edge in edges:
                if edge.source_handle == handle_id:
                    return edge.target, edge.target_handle

            # Fallback for multi-input: try single-input format
            if input_count > 1:
                fallback_handle = f"handle-{condition_index}"
                for edge in edges:
                    if edge.source_handle == fallback_handle:
                        logger.warning(
                            "Node '%s' (input_count=%d) uses the single-input fallback "
                            "handle '%s' au lieu de '%s'",
                            source_id, input_count, fallback_handle, handle_id,
                        )
                        return edge.target, edge.target_handle

        # Fallback: find the edge with the matching label
        for edge in edges:
            if edge.label == condition_label:
                return edge.target, edge.target_handle

        # Fallback: take the first edge without label (default)
        for edge in edges:
            if edge.label is None:
                return edge.target, edge.target_handle

        return None, None

    def get_required_fields(self) -> set[str]:
        """Return the list of fields required by the tree."""
        fields = set()
        for node in self.nodes.values():
            if hasattr(node, "config"):
                if "field" in node.config:
                    fields.add(node.config["field"])
                if "lookup_key" in node.config:
                    fields.add(node.config["lookup_key"])
                if node.type == NodeType.EQUATION and "variables" in node.config:
                    for var in node.config["variables"]:
                        fields.add(var)
        return fields

    def get_lookup_tables(self) -> set[str]:
        """Return the list of lookup tables used."""
        tables = set()
        for node in self.nodes.values():
            if hasattr(node, "config") and "lookup_table" in node.config:
                tables.add(node.config["lookup_table"])
        return tables
