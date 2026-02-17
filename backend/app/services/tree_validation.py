"""
Validation de la structure d'un arbre de décision.
Retourne des warnings (non bloquants) pour ne pas casser les arbres existants.
"""

from app.engine.formula import FormulaError, validate_formula
from app.schemas.tree import NodeType, TreeStructure


def validate_tree_structure(structure: TreeStructure) -> list[str]:
    """
    Valide la structure d'un arbre et retourne une liste de warnings.

    Validations effectuées :
    - Edges référencent des nœuds existants
    - Source handles correspondent aux conditions du nœud source
    - Au moins un nœud racine (non ciblé par aucune edge)
    - Détection de cycles (DFS)
    - Au moins un nœud output
    """
    warnings: list[str] = []

    if not structure.nodes:
        warnings.append("L'arbre ne contient aucun nœud")
        return warnings

    node_ids = {n.id for n in structure.nodes}
    node_map = {n.id: n for n in structure.nodes}

    # Vérifie les edges
    for edge in structure.edges:
        if edge.source not in node_ids:
            warnings.append(
                f"L'edge '{edge.id}' référence un nœud source inexistant: '{edge.source}'"
            )
        if edge.target not in node_ids:
            warnings.append(
                f"L'edge '{edge.id}' référence un nœud cible inexistant: '{edge.target}'"
            )

    # Vérifie les source_handles
    for edge in structure.edges:
        if edge.source_handle and edge.source in node_map:
            source_node = node_map[edge.source]
            if source_node.type == NodeType.OUTPUT:
                warnings.append(
                    f"L'edge '{edge.id}' sort d'un nœud output '{edge.source}'"
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
                                f"mais le nœud '{edge.source}' a input_count={input_count}"
                            )
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(
                                f"L'edge '{edge.id}' utilise condition_index={cond_idx} "
                                f"mais le nœud '{edge.source}' a {len(source_node.conditions)} conditions"
                            )
                    elif len(parts) == 1:
                        cond_idx = int(parts[0])
                        if cond_idx >= len(source_node.conditions):
                            warnings.append(
                                f"L'edge '{edge.id}' utilise condition_index={cond_idx} "
                                f"mais le nœud '{edge.source}' a {len(source_node.conditions)} conditions"
                            )
                except ValueError:
                    warnings.append(
                        f"L'edge '{edge.id}' a un source_handle invalide: '{handle}'"
                    )

    # Vérifie nœud racine
    target_nodes = {e.target for e in structure.edges}
    root_nodes = [nid for nid in node_ids if nid not in target_nodes]
    if not root_nodes:
        warnings.append("Aucun nœud racine détecté (tous les nœuds sont ciblés par des edges)")

    # Valide les noeuds equation
    for node in structure.nodes:
        if node.type == NodeType.EQUATION:
            formula = node.config.get("formula", "")
            if not formula or not formula.strip():
                warnings.append(
                    f"Le nœud equation '{node.id}' n'a pas de formule configurée"
                )
            else:
                try:
                    validate_formula(formula)
                except FormulaError as e:
                    warnings.append(
                        f"Le nœud equation '{node.id}' a une formule invalide : {e}"
                    )

    # Vérifie au moins un nœud output
    output_nodes = [n for n in structure.nodes if n.type == NodeType.OUTPUT]
    if not output_nodes:
        warnings.append("L'arbre ne contient aucun nœud de sortie (output)")

    # Détection de cycles (DFS)
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
                warnings.append("Cycle détecté dans l'arbre — risque de boucle infinie lors de l'évaluation")
                break

    return warnings
