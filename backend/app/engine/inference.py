"""
Moteur d'inférence pour l'évaluation des vulnérabilités.
"""

from typing import Any

from app.engine.nodes import BaseNode, NodeEvaluationError, OutputNode, create_node
from app.schemas.evaluation import DecisionPath, EvaluationResult
from app.schemas.tree import EdgeSchema, NodeSchema, NodeType, TreeStructure
from app.schemas.vulnerability import VulnerabilityInput


class InferenceEngine:
    """
    Moteur d'inférence qui charge un arbre et évalue des vulnérabilités.
    """

    def __init__(self, tree_structure: TreeStructure):
        self.tree_structure = tree_structure
        self.nodes: dict[str, BaseNode] = {}
        self.edges: dict[str, list[EdgeSchema]] = {}  # source_id -> [edges]
        self.root_node_id: str | None = None

        self._build_tree()

    def _build_tree(self) -> None:
        """Construit la structure interne de l'arbre."""
        # Crée les nœuds
        for node_schema in self.tree_structure.nodes:
            self.nodes[node_schema.id] = create_node(node_schema)

        # Indexe les edges par source
        for edge in self.tree_structure.edges:
            if edge.source not in self.edges:
                self.edges[edge.source] = []
            self.edges[edge.source].append(edge)

        # Trouve le nœud racine (celui qui n'est la cible d'aucune edge)
        target_nodes = {e.target for e in self.tree_structure.edges}
        for node_id in self.nodes:
            if node_id not in target_nodes:
                self.root_node_id = node_id
                break

        if self.root_node_id is None and self.nodes:
            # Si pas de racine claire, prend le premier nœud INPUT
            for node_id, node in self.nodes.items():
                if node.type == NodeType.INPUT:
                    self.root_node_id = node_id
                    break

    def evaluate(
        self,
        vulnerability: VulnerabilityInput,
        lookups: dict[str, dict[str, dict[str, Any]]] | None = None,
        include_path: bool = True,
    ) -> EvaluationResult:
        """
        Évalue une vulnérabilité en traversant l'arbre.

        Args:
            vulnerability: La vulnérabilité à évaluer
            lookups: Cache de lookup préchargé {table: {key: {field: value}}}
            include_path: Si True, inclut le chemin de décision (audit trail)

        Returns:
            EvaluationResult avec la décision et le chemin
        """
        # Identifiant de la vulnérabilité (id ou cve_id comme fallback)
        vuln_id = vulnerability.id or vulnerability.cve_id

        if not self.root_node_id:
            return EvaluationResult(
                vuln_id=vuln_id,
                decision="Error",
                error="Arbre vide ou invalide",
            )

        # Prépare le contexte
        context = {
            "vulnerability": vulnerability.model_dump(),
            "lookups": lookups or {},
        }

        path: list[DecisionPath] = []
        current_node_id = self.root_node_id
        current_input_index: int | None = None  # Track which input we entered through

        # Limite de sécurité contre les boucles infinies
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
                    error=f"Nœud {current_node_id} non trouvé",
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

            # Si c'est un nœud OUTPUT, on a terminé
            if isinstance(node, OutputNode):
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision=str(value),
                    decision_color=node.config.get("color"),
                    path=path if include_path else [],
                )

            # Trouve l'index de la condition matchée
            condition_index = None
            if condition_label and hasattr(node, "conditions"):
                for idx, cond in enumerate(node.conditions):
                    if cond.label == condition_label:
                        condition_index = idx
                        break

            # Check if this is a multi-input node
            input_count = node.config.get("input_count", 1) if hasattr(node, "config") else 1

            # Trouve l'edge à suivre basé sur la condition et l'input_index
            next_node_id, next_target_handle = self._find_next_node(
                current_node_id, condition_label, condition_index, current_input_index, input_count
            )
            if next_node_id is None:
                return EvaluationResult(
                    vuln_id=vuln_id,
                    decision="Error",
                    path=path if include_path else [],
                    error=f"Aucune branche pour la condition '{condition_label}' du nœud {node.id}",
                )

            current_node_id = next_node_id
            # Parse the target_handle to get the input index for the next node
            current_input_index = self._parse_input_index(next_target_handle)

        return EvaluationResult(
            vuln_id=vuln_id,
            decision="Error",
            path=path if include_path else [],
            error="Limite d'itérations atteinte (boucle infinie détectée?)",
        )

    def _parse_input_index(self, target_handle: str | None) -> int | None:
        """Parse input index from target_handle (e.g., 'input-2' -> 2)."""
        if not target_handle:
            return None
        if target_handle.startswith("input-"):
            try:
                return int(target_handle.split("-")[1])
            except (IndexError, ValueError):
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
        Trouve le nœud suivant basé sur la condition matchée.

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

        # Si une seule edge, on la prend
        if len(edges) == 1:
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
                        return edge.target, edge.target_handle

        # Fallback: cherche l'edge avec le bon label
        for edge in edges:
            if edge.label == condition_label:
                return edge.target, edge.target_handle

        # Fallback: prend la première edge sans label (default)
        for edge in edges:
            if edge.label is None:
                return edge.target, edge.target_handle

        return None, None

    def get_required_fields(self) -> set[str]:
        """Retourne la liste des champs requis par l'arbre."""
        fields = set()
        for node in self.nodes.values():
            if hasattr(node, "config"):
                if "field" in node.config:
                    fields.add(node.config["field"])
                if "lookup_key" in node.config:
                    fields.add(node.config["lookup_key"])
        return fields

    def get_lookup_tables(self) -> set[str]:
        """Retourne la liste des tables de lookup utilisées."""
        tables = set()
        for node in self.nodes.values():
            if hasattr(node, "config") and "lookup_table" in node.config:
                tables.add(node.config["lookup_table"])
        return tables
