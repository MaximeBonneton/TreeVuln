"""
Diagnostic complet d'un arbre de decision.
Orchestre les checks structurels, de configuration et logiques.
"""

from app.schemas.diagnostic import DiagnosticItem, DiagnosticResult
from app.schemas.tree import ConditionOperator, NodeType, TreeStructure

# Operateurs numeriques pour la detection de trous/chevauchements
_NUMERIC_OPS = {
    ConditionOperator.GREATER_THAN,
    ConditionOperator.GREATER_THAN_OR_EQUAL,
    ConditionOperator.LESS_THAN,
    ConditionOperator.LESS_THAN_OR_EQUAL,
}


def diagnose_tree(structure: TreeStructure) -> DiagnosticResult:
    """Analyse complete d'un arbre. Retourne erreurs et warnings."""
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
    """Checks structurels : edges, cycles, racine, output."""
    if not structure.nodes:
        errors.append(DiagnosticItem(
            code="NO_ROOT", message="L'arbre ne contient aucun noeud", severity="error",
        ))
        return

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Edges invalides
    for edge in structure.edges:
        if edge.source not in node_ids:
            errors.append(DiagnosticItem(
                code="EDGE_SOURCE_MISSING",
                message=f"L'edge '{edge.id}' reference un noeud source inexistant: '{edge.source}'",
                severity="error", edge_id=edge.id,
            ))
        if edge.target not in node_ids:
            errors.append(DiagnosticItem(
                code="EDGE_TARGET_MISSING",
                message=f"L'edge '{edge.id}' reference un noeud cible inexistant: '{edge.target}'",
                severity="error", edge_id=edge.id,
            ))

    # Edge depuis un output
    for edge in structure.edges:
        if edge.source in node_map and node_map[edge.source].type == NodeType.OUTPUT:
            warnings.append(DiagnosticItem(
                code="EDGE_FROM_OUTPUT",
                message=f"L'edge '{edge.id}' sort d'un noeud output '{edge.source}'",
                severity="warning", node_id=edge.source, edge_id=edge.id,
            ))

    # Handles invalides
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
                                message=f"L'edge '{edge.id}' utilise condition_index={cond_idx} mais le noeud '{edge.source}' a {len(source_node.conditions)} conditions",
                                severity="warning", node_id=edge.source, edge_id=edge.id,
                            ))
                    elif len(parts) == 1:
                        cond_idx = int(parts[0])
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(DiagnosticItem(
                                code="INVALID_SOURCE_HANDLE",
                                message=f"L'edge '{edge.id}' utilise condition_index={cond_idx} mais le noeud '{edge.source}' a {len(source_node.conditions)} conditions",
                                severity="warning", node_id=edge.source, edge_id=edge.id,
                            ))
                except ValueError:
                    warnings.append(DiagnosticItem(
                        code="INVALID_SOURCE_HANDLE",
                        message=f"L'edge '{edge.id}' a un source_handle invalide: '{handle}'",
                        severity="warning", edge_id=edge.id,
                    ))

    # Noeud racine
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    if not root_nodes:
        errors.append(DiagnosticItem(
            code="NO_ROOT",
            message="Aucun noeud racine detecte (tous les noeuds sont cibles par des edges)",
            severity="error",
        ))

    # Noeud output
    output_nodes = [n for n in structure.nodes if n.type == NodeType.OUTPUT]
    if not output_nodes:
        errors.append(DiagnosticItem(
            code="NO_OUTPUT",
            message="L'arbre ne contient aucun noeud de sortie (output)",
            severity="error",
        ))

    # Detection de cycles (DFS)
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
                    message="Cycle detecte dans l'arbre - risque de boucle infinie",
                    severity="error",
                ))
                break


def _check_configuration(
    structure: TreeStructure,
    errors: list[DiagnosticItem],
    warnings: list[DiagnosticItem],
) -> None:
    """Checks de configuration : champs manquants, noeuds isoles, handles orphelins."""
    if not structure.nodes:
        return

    node_ids = {n.id for n in structure.nodes}

    # Noeuds connectes (source ou target d'une edge)
    connected_nodes: set[str] = set()
    for edge in structure.edges:
        connected_nodes.add(edge.source)
        connected_nodes.add(edge.target)

    # Edges sortantes par noeud, indexees par source_handle
    outgoing_handles: dict[str, set[str]] = {n.id: set() for n in structure.nodes}
    for edge in structure.edges:
        if edge.source in node_ids and edge.source_handle:
            outgoing_handles[edge.source].add(edge.source_handle)

    for node in structure.nodes:
        # Noeuds non-output sans conditions de sortie
        if node.type in (NodeType.INPUT, NodeType.LOOKUP, NodeType.EQUATION) and not node.conditions:
            errors.append(DiagnosticItem(
                code="NO_CONDITIONS",
                message=f"Le noeud '{node.id}' ({node.label}) n'a aucune condition de sortie",
                severity="error", node_id=node.id,
            ))

        # Config manquante
        if node.type == NodeType.INPUT:
            field = node.config.get("field")
            if not field or not str(field).strip():
                errors.append(DiagnosticItem(
                    code="INPUT_NO_FIELD",
                    message=f"Le noeud input '{node.id}' n'a pas de champ configure",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.LOOKUP:
            required = ["lookup_table", "lookup_key", "lookup_field"]
            missing = [k for k in required if not node.config.get(k)]
            if missing:
                errors.append(DiagnosticItem(
                    code="LOOKUP_INCOMPLETE",
                    message=f"Le noeud lookup '{node.id}' manque: {', '.join(missing)}",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.OUTPUT:
            decision = node.config.get("decision")
            if not decision or not str(decision).strip():
                errors.append(DiagnosticItem(
                    code="OUTPUT_NO_DECISION",
                    message=f"Le noeud output '{node.id}' n'a pas de decision configuree",
                    severity="error", node_id=node.id,
                ))

        elif node.type == NodeType.EQUATION:
            formula = node.config.get("formula")
            if not formula or not str(formula).strip():
                errors.append(DiagnosticItem(
                    code="EQUATION_NO_FORMULA",
                    message=f"Le noeud equation '{node.id}' n'a pas de formule configuree",
                    severity="error", node_id=node.id,
                ))

        # Noeud isole
        if node.id not in connected_nodes:
            warnings.append(DiagnosticItem(
                code="ISOLATED_NODE",
                message=f"Le noeud '{node.id}' ({node.label}) n'est connecte a aucune edge",
                severity="warning", node_id=node.id,
            ))

        # Handles orphelins (conditions sans edge)
        if node.type != NodeType.OUTPUT and node.conditions:
            input_count = node.config.get("input_count", 1)
            for cond_idx in range(len(node.conditions)):
                if input_count > 1:
                    for input_idx in range(input_count):
                        expected = f"handle-{input_idx}-{cond_idx}"
                        if expected not in outgoing_handles.get(node.id, set()):
                            warnings.append(DiagnosticItem(
                                code="ORPHAN_HANDLE",
                                message=f"La condition '{node.conditions[cond_idx].label}' (entree {input_idx}) du noeud '{node.id}' n'a pas d'edge connectee",
                                severity="warning", node_id=node.id,
                            ))
                else:
                    expected = f"handle-{cond_idx}"
                    if expected not in outgoing_handles.get(node.id, set()):
                        warnings.append(DiagnosticItem(
                            code="ORPHAN_HANDLE",
                            message=f"La condition '{node.conditions[cond_idx].label}' du noeud '{node.id}' n'a pas d'edge connectee",
                            severity="warning", node_id=node.id,
                        ))


def _check_logic(
    structure: TreeStructure,
    errors: list[DiagnosticItem],
    warnings: list[DiagnosticItem],
) -> None:
    """Checks logiques : branches mortes, trous/chevauchements numeriques, branchement unique."""
    if not structure.nodes:
        return

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Adjacence
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for edge in structure.edges:
        if edge.source in node_ids and edge.target in node_ids:
            adj[edge.source].append(edge.target)

    # Branches mortes
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    output_ids = {n.id for n in structure.nodes if n.type == NodeType.OUTPUT}

    for root_id in root_nodes:
        _find_dead_branches(root_id, adj, output_ids, set(), warnings, node_map)

    # Checks par noeud
    for node in structure.nodes:
        if node.type == NodeType.OUTPUT:
            continue

        # Branchement unique
        if len(node.conditions) == 1:
            warnings.append(DiagnosticItem(
                code="SINGLE_CONDITION",
                message=f"Le noeud '{node.id}' ({node.label}) n'a qu'une seule condition de sortie",
                severity="warning", node_id=node.id,
            ))

        # Analyse numerique
        _check_numeric_conditions(node, warnings)


def _find_dead_branches(
    node_id: str,
    adj: dict[str, list[str]],
    output_ids: set[str],
    visited: set[str],
    warnings: list[DiagnosticItem],
    node_map: dict,
) -> bool:
    """Retourne True si le noeud peut atteindre un output."""
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
                message=f"Le noeud '{node_id}' ({node_map[node_id].label}) ne mene a aucun noeud output",
                severity="warning", node_id=node_id,
            ))
        return False

    all_reach = True
    for child in children:
        if not _find_dead_branches(child, adj, output_ids, visited.copy(), warnings, node_map):
            all_reach = False

    return all_reach


def _check_numeric_conditions(node, warnings: list[DiagnosticItem]) -> None:
    """Detecte les trous et chevauchements dans les conditions numeriques d'un noeud."""
    if len(node.conditions) < 2:
        return

    intervals = []
    for cond in node.conditions:
        if cond.logic is not None or cond.operator is None:
            return  # Conditions composees : on skip
        if cond.operator not in _NUMERIC_OPS:
            return  # Pas entierement numerique
        try:
            val = float(cond.value)
        except (TypeError, ValueError):
            return
        intervals.append((cond.operator, val))

    if len(intervals) < 2:
        return

    # Construire les bornes inferieures/superieures
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

    # Trous
    for upper_val, upper_incl in uppers:
        for lower_val, lower_incl in lowers:
            if upper_val < lower_val:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_GAP",
                    message=f"Trou dans les conditions du noeud '{node.id}': aucune condition ne couvre les valeurs entre {upper_val} et {lower_val}",
                    severity="warning", node_id=node.id,
                ))
            elif upper_val == lower_val and not upper_incl and not lower_incl:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_GAP",
                    message=f"Trou dans les conditions du noeud '{node.id}': la valeur {upper_val} n'est couverte par aucune condition",
                    severity="warning", node_id=node.id,
                ))

    # Chevauchements
    for lower_val, lower_incl in lowers:
        for upper_val, upper_incl in uppers:
            if lower_val < upper_val:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_OVERLAP",
                    message=f"Chevauchement dans les conditions du noeud '{node.id}': les valeurs entre {lower_val} et {upper_val} correspondent a plusieurs conditions",
                    severity="warning", node_id=node.id,
                ))
            elif lower_val == upper_val and lower_incl and upper_incl:
                warnings.append(DiagnosticItem(
                    code="NUMERIC_OVERLAP",
                    message=f"Chevauchement dans les conditions du noeud '{node.id}': la valeur {lower_val} correspond a plusieurs conditions",
                    severity="warning", node_id=node.id,
                ))
