"""
Validation of a decision tree structure.
Returns warnings (non-blocking) to avoid breaking existing trees.
"""

from app.engine.formula import FormulaError, validate_formula
from app.schemas.tree import NodeType, TreeStructure


def validate_tree_structure(structure: TreeStructure) -> list[str]:
    """
    Validate a tree structure and return a list of warnings.

    Validations performed:
    - Edges reference existing nodes
    - Source handles match the source node conditions
    - At least one root node (not targeted by any edge)
    - Cycle detection (DFS)
    - At least one output node
    """
    warnings: list[str] = []

    if not structure.nodes:
        warnings.append("The tree contains no nodes")
        return warnings

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Check edges
    for edge in structure.edges:
        if edge.source not in node_ids:
            warnings.append(
                f"Edge '{edge.id}' references a non-existent source node: '{edge.source}'"
            )
        if edge.target not in node_ids:
            warnings.append(
                f"Edge '{edge.id}' references a non-existent target node: '{edge.target}'"
            )

    # Check source_handles
    for edge in structure.edges:
        if edge.source_handle and edge.source in node_map:
            source_node = node_map[edge.source]
            if source_node.type == NodeType.OUTPUT:
                warnings.append(
                    f"Edge '{edge.id}' exits an output node '{edge.source}'"
                )
                continue

            input_count = source_node.config.get("input_count", 1)
            handle = edge.source_handle

            if handle.startswith("handle-"):
                parts = handle.replace("handle-", "").split("-")
                try:
                    if input_count > 1 and len(parts) == 2:
                        input_idx, cond_idx = int(parts[0]), int(parts[1])
                        if input_idx >= input_count:
                            warnings.append(
                                f"L'edge '{edge.id}' utilise input_index={input_idx} "
                                f"but node '{edge.source}' has input_count={input_count}"
                            )
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(
                                f"L'edge '{edge.id}' utilise condition_index={cond_idx} "
                                f"but node '{edge.source}' has {len(source_node.conditions)} conditions"
                            )
                    elif len(parts) == 1:
                        cond_idx = int(parts[0])
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(
                                f"L'edge '{edge.id}' utilise condition_index={cond_idx} "
                                f"but node '{edge.source}' has {len(source_node.conditions)} conditions"
                            )
                except ValueError:
                    warnings.append(
                        f"Edge '{edge.id}' has an invalid source_handle: '{handle}'"
                    )

    # Check root node
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    if not root_nodes:
        warnings.append("No root node detected (all nodes are targeted by edges)")

    # Validate equation nodes
    for node in structure.nodes:
        if node.type == NodeType.EQUATION:
            formula = node.config.get("formula", "")
            if not formula or not formula.strip():
                warnings.append(
                    f"Equation node '{node.id}' has no formula configured"
                )
            else:
                try:
                    validate_formula(formula)
                except FormulaError as e:
                    warnings.append(
                        f"Equation node '{node.id}' has an invalid formula: {e}"
                    )

    # Check for at least one output node
    output_nodes = [n for n in structure.nodes if n.type == NodeType.OUTPUT]
    if not output_nodes:
        warnings.append("The tree contains no output nodes")

    # Cycle detection (DFS)
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in structure.edges:
        if edge.source in node_ids and edge.target in node_ids:
            adj[edge.source].append(edge.target)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}

    def has_cycle(node_id: str) -> bool:
        color[node_id] = GRAY
        for neighbor in adj[node_id]:
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and has_cycle(neighbor):
                return True
        color[node_id] = BLACK
        return False

    for nid in node_ids:
        if color[nid] == WHITE:
            if has_cycle(nid):
                warnings.append("Cycle detected in tree — risk of infinite loop during evaluation")
                break

    return warnings
