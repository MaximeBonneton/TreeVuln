"""
Complete diagnostic of a decision tree.
Orchestrates structural, configuration and logic checks.
"""

from app.schemas.diagnostic import DiagnosticItem, DiagnosticResult
from app.schemas.tree import ConditionOperator, NodeType, TreeStructure

# Numeric operators for gap/overlap detection
_NUMERIC_OPS = {
    ConditionOperator.GREATER_THAN,
    ConditionOperator.GREATER_THAN_OR_EQUAL,
    ConditionOperator.LESS_THAN,
    ConditionOperator.LESS_THAN_OR_EQUAL,
}


def _get_numeric_fields(structure: TreeStructure) -> set[str]:
    """Extract numeric or boolean field names from the field mapping in metadata."""
    mapping_data = structure.metadata.get("field_mapping")
    if not mapping_data:
        return set()
    fields = mapping_data.get("fields", [])
    numeric_types = {"number", "boolean"}
    return {f["name"] for f in fields if isinstance(f, dict) and f.get("type") in numeric_types}


def diagnose_tree(structure: TreeStructure) -> DiagnosticResult:
    """Complete analysis of a tree. Returns errors and warnings."""
    errors: list[DiagnosticItem] = []
    warnings: list[DiagnosticItem] = []

    _check_structural(structure, errors, warnings)
    _check_configuration(structure, errors, warnings)
    _check_logic(structure, errors, warnings)

    return DiagnosticResult(errors=errors, warnings=warnings)


def _check_structural(
    structure: TreeStructure,
    errors: list[DiagnosticItem],
    warnings: list[DiagnosticItem],
) -> None:
    """Structural checks: edges, cycles, root, output."""
    if not structure.nodes:
        errors.append(DiagnosticItem(
            code="NO_ROOT", message="The tree contains no nodes", severity="error",
        ))
        return

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Invalid edges
    for edge in structure.edges:
        if edge.source not in node_ids:
            errors.append(DiagnosticItem(
                code="EDGE_SOURCE_MISSING",
                message=f"Edge '{edge.id}' references a non-existent source node: '{edge.source}'",
                severity="error", edge_id=edge.id,
            ))
        if edge.target not in node_ids:
            errors.append(DiagnosticItem(
                code="EDGE_TARGET_MISSING",
                message=f"Edge '{edge.id}' references a non-existent target node: '{edge.target}'",
                severity="error", edge_id=edge.id,
            ))

    # Edge from an output node
    for edge in structure.edges:
        if edge.source in node_map and node_map[edge.source].type == NodeType.OUTPUT:
            warnings.append(DiagnosticItem(
                code="EDGE_FROM_OUTPUT",
                message=f"Edge '{edge.id}' originates from an output node '{edge.source}'",
                severity="warning", node_id=edge.source, edge_id=edge.id,
            ))

    # Invalid handles
    for edge in structure.edges:
        if edge.source_handle and edge.source in node_map:
            source_node = node_map[edge.source]
            if source_node.type == NodeType.OUTPUT:
                continue
            input_count = source_node.config.get("input_count", 1)
            handle = edge.source_handle
            if handle.startswith("handle-"):
                parts = handle.replace("handle-", "").split("-")
                try:
                    if input_count > 1 and len(parts) == 2:
                        cond_idx = int(parts[1])
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(DiagnosticItem(
                                code="INVALID_SOURCE_HANDLE",
                                message=f"Edge '{edge.id}' uses condition_index={cond_idx} but node '{edge.source}' has {len(source_node.conditions)} conditions",
                                severity="warning", node_id=edge.source, edge_id=edge.id,
                            ))
                    elif len(parts) == 1:
                        cond_idx = int(parts[0])
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(DiagnosticItem(
                                code="INVALID_SOURCE_HANDLE",
                                message=f"Edge '{edge.id}' uses condition_index={cond_idx} but node '{edge.source}' has {len(source_node.conditions)} conditions",
                                severity="warning", node_id=edge.source, edge_id=edge.id,
                            ))
                except ValueError:
                    warnings.append(DiagnosticItem(
                        code="INVALID_SOURCE_HANDLE",
                        message=f"Edge '{edge.id}' has an invalid source_handle: '{handle}'",
                        severity="warning", edge_id=edge.id,
                    ))

    # Root node
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    if not root_nodes:
        errors.append(DiagnosticItem(
            code="NO_ROOT",
            message="No root node detected (all nodes are targets of edges)",
            severity="error",
        ))

    # Output node
    output_nodes = [n for n in structure.nodes if n.type == NodeType.OUTPUT]
    if not output_nodes:
        errors.append(DiagnosticItem(
            code="NO_OUTPUT",
            message="The tree contains no output nodes",
            severity="error",
        ))

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
                errors.append(DiagnosticItem(
                    code="CYCLE_DETECTED",
                    message="Cycle detected in the tree - risk of infinite loop",
                    severity="error",
                ))
                break


def _check_configuration(
    structure: TreeStructure,
    errors: list[DiagnosticItem],
    warnings: list[DiagnosticItem],
) -> None:
    """Configuration checks: missing fields, isolated nodes, orphan handles."""
    if not structure.nodes:
        return

    node_ids = {n.id for n in structure.nodes}

    # Connected nodes (source or target of an edge)
    connected_nodes: set[str] = set()
    for edge in structure.edges:
        connected_nodes.add(edge.source)
        connected_nodes.add(edge.target)

    # Outgoing edges per node, indexed by source_handle
    outgoing_handles: dict[str, set[str]] = {n.id: set() for n in structure.nodes}
    # Nodes that have at least one outgoing edge without source_handle
    has_unhandled_edges: set[str] = set()
    for edge in structure.edges:
        if edge.source in node_ids:
            if edge.source_handle:
                outgoing_handles[edge.source].add(edge.source_handle)
            else:
                has_unhandled_edges.add(edge.source)

    for node in structure.nodes:
        # Non-output nodes without exit conditions
        if node.type in (NodeType.INPUT, NodeType.LOOKUP, NodeType.EQUATION) and not node.conditions:
            errors.append(DiagnosticItem(
                code="NO_CONDITIONS",
                message=f"Node '{node.id}' ({node.label}) has no exit conditions",
                severity="error", node_id=node.id,
            ))

        # Missing configuration
        if node.type == NodeType.INPUT:
            field = node.config.get("field")
            if not field or not str(field).strip():
                errors.append(DiagnosticItem(
                    code="INPUT_NO_FIELD",
                    message=f"Input node '{node.id}' has no field configured",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.LOOKUP:
            required = ["lookup_table", "lookup_key", "lookup_field"]
            missing = [k for k in required if not node.config.get(k)]
            if missing:
                errors.append(DiagnosticItem(
                    code="LOOKUP_INCOMPLETE",
                    message=f"Lookup node '{node.id}' is missing: {', '.join(missing)}",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.OUTPUT:
            decision = node.config.get("decision")
            if not decision or not str(decision).strip():
                errors.append(DiagnosticItem(
                    code="OUTPUT_NO_DECISION",
                    message=f"Output node '{node.id}' has no decision configured",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.EQUATION:
            formula = node.config.get("formula")
            if not formula or not str(formula).strip():
                errors.append(DiagnosticItem(
                    code="EQUATION_NO_FORMULA",
                    message=f"Equation node '{node.id}' has no formula configured",
                    severity="error", node_id=node.id,
                ))
            # Variables without value_map: risk of text in a numeric calculation
            # Skip variables known as numeric or boolean via the field mapping
            variables = node.config.get("variables", [])
            value_maps = node.config.get("value_maps", {})
            numeric_fields = _get_numeric_fields(structure)
            for var_name in variables:
                if var_name not in value_maps and var_name not in numeric_fields:
                    warnings.append(DiagnosticItem(
                        code="EQUATION_NO_VALUE_MAP",
                        message=f"Variable '{var_name}' of equation node '{node.id}' has no text-to-number mapping (value_map). If this field contains text, evaluation will fail.",
                        severity="warning", node_id=node.id,
                    ))

        # Isolated node
        if node.id not in connected_nodes:
            warnings.append(DiagnosticItem(
                code="ISOLATED_NODE",
                message=f"Node '{node.id}' ({node.label}) is not connected to any edge",
                severity="warning", node_id=node.id,
            ))

        # Orphan handles (conditions without edge)
        # Skip if the node has outgoing edges without source_handle (we cannot determine the mapping)
        if node.type != NodeType.OUTPUT and node.conditions and node.id not in has_unhandled_edges:
            input_count = node.config.get("input_count", 1)
            for cond_idx in range(len(node.conditions)):
                if input_count > 1:
                    for input_idx in range(input_count):
                        expected = f"handle-{input_idx}-{cond_idx}"
                        if expected not in outgoing_handles.get(node.id, set()):
                            warnings.append(DiagnosticItem(
                                code="ORPHAN_HANDLE",
                                message=f"Condition '{node.conditions[cond_idx].label}' (input {input_idx}) of node '{node.id}' has no connected edge",
                                severity="warning", node_id=node.id,
                            ))
                else:
                    expected = f"handle-{cond_idx}"
                    if expected not in outgoing_handles.get(node.id, set()):
                        warnings.append(DiagnosticItem(
                            code="ORPHAN_HANDLE",
                            message=f"Condition '{node.conditions[cond_idx].label}' of node '{node.id}' has no connected edge",
                            severity="warning", node_id=node.id,
                        ))


def _check_logic(
    structure: TreeStructure,
    errors: list[DiagnosticItem],
    warnings: list[DiagnosticItem],
) -> None:
    """Logic checks: dead branches, numeric gaps/overlaps, single branching."""
    if not structure.nodes:
        return

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Adjacency
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in structure.edges:
        if edge.source in node_ids and edge.target in node_ids:
            adj[edge.source].append(edge.target)

    # Dead branches
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    output_ids = {n.id for n in structure.nodes if n.type == NodeType.OUTPUT}

    for root_id in root_nodes:
        _find_dead_branches(root_id, adj, output_ids, set(), warnings, node_map)

    # Per-node checks
    for node in structure.nodes:
        if node.type == NodeType.OUTPUT:
            continue

        # Single branching
        if len(node.conditions) == 1:
            warnings.append(DiagnosticItem(
                code="SINGLE_CONDITION",
                message=f"Node '{node.id}' ({node.label}) has only one exit condition",
                severity="warning", node_id=node.id,
            ))

        # Numeric analysis
        _check_numeric_conditions(node, warnings)


def _find_dead_branches(
    node_id: str,
    adj: dict[str, list[str]],
    output_ids: set[str],
    visited: set[str],
    warnings: list[DiagnosticItem],
    node_map: dict,
) -> bool:
    """Returns True if the node can reach an output."""
    if node_id in output_ids:
        return True
    if node_id in visited:
        return False

    visited.add(node_id)
    children = adj.get(node_id, [])

    if not children:
        if node_id in node_map:
            warnings.append(DiagnosticItem(
                code="DEAD_BRANCH",
                message=f"Node '{node_id}' ({node_map[node_id].label}) does not lead to any output node",
                severity="warning", node_id=node_id,
            ))
        return False

    all_reach = True
    for child in children:
        if not _find_dead_branches(child, adj, output_ids, visited.copy(), warnings, node_map):
            all_reach = False

    return all_reach


def _check_numeric_conditions(node, warnings: list[DiagnosticItem]) -> None:
    """Detects gaps and overlaps in the numeric conditions of a node."""
    if len(node.conditions) < 2:
        return

    intervals = []
    for cond in node.conditions:
        if cond.logic is not None or cond.operator is None:
            return  # Compound conditions: skip
        if cond.operator not in _NUMERIC_OPS:
            return  # Not entirely numeric
        try:
            val = float(cond.value)
        except (TypeError, ValueError):
            return
        intervals.append((cond.operator, val))

    if len(intervals) < 2:
        return

    # Build lower/upper bounds
    lowers = []  # (val, inclusive)
    uppers = []  # (val, inclusive)
    for op, val in intervals:
        if op == ConditionOperator.GREATER_THAN:
            lowers.append((val, False))
        elif op == ConditionOperator.GREATER_THAN_OR_EQUAL:
            lowers.append((val, True))
        elif op == ConditionOperator.LESS_THAN:
            uppers.append((val, False))
        elif op == ConditionOperator.LESS_THAN_OR_EQUAL:
            uppers.append((val, True))

    # Gaps
    for upper_val, upper_incl in uppers:
        for lower_val, lower_incl in lowers:
            if upper_val < lower_val:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_GAP",
                    message=f"Gap in conditions of node '{node.id}': no condition covers values between {upper_val} and {lower_val}",
                    severity="warning", node_id=node.id,
                ))
            elif upper_val == lower_val and not upper_incl and not lower_incl:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_GAP",
                    message=f"Gap in conditions of node '{node.id}': value {upper_val} is not covered by any condition",
                    severity="warning", node_id=node.id,
                ))

    # Overlaps
    for lower_val, lower_incl in lowers:
        for upper_val, upper_incl in uppers:
            if lower_val < upper_val:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_OVERLAP",
                    message=f"Overlap in conditions of node '{node.id}': values between {lower_val} and {upper_val} match multiple conditions",
                    severity="warning", node_id=node.id,
                ))
            elif lower_val == upper_val and lower_incl and upper_incl:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_OVERLAP",
                    message=f"Overlap in conditions of node '{node.id}': value {lower_val} matches multiple conditions",
                    severity="warning", node_id=node.id,
                ))
