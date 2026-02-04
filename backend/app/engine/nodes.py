"""
Définition des types de nœuds et de leur logique d'évaluation.
"""

import re
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.tree import ConditionOperator, NodeCondition, NodeSchema, NodeType


class NodeEvaluationError(Exception):
    """Erreur lors de l'évaluation d'un nœud."""

    pass


class BaseNode(ABC):
    """Classe de base pour tous les types de nœuds."""

    def __init__(self, schema: NodeSchema):
        self.id = schema.id
        self.label = schema.label
        self.type = schema.type
        self.config = schema.config
        self.conditions = schema.conditions

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        """
        Évalue le nœud avec le contexte donné.

        Args:
            context: Dictionnaire contenant les données de la vulnérabilité
                     et les résultats des lookups.

        Returns:
            Tuple (valeur_évaluée, condition_label_matchée)
            Pour un nœud OUTPUT, retourne (décision, None)
        """
        pass

    def match_condition(self, value: Any) -> tuple[int, str] | None:
        """
        Trouve la condition qui correspond à la valeur.

        Returns:
            Tuple (index_condition, label_condition) ou None si aucune ne matche.
        """
        for idx, condition in enumerate(self.conditions):
            if self._evaluate_condition(value, condition):
                return idx, condition.label
        return None

    def _evaluate_condition(self, value: Any, condition: NodeCondition) -> bool:
        """Évalue si une valeur satisfait une condition."""
        op = condition.operator
        cond_value = condition.value

        # Gestion des valeurs nulles
        if op == ConditionOperator.IS_NULL:
            return value is None
        if op == ConditionOperator.IS_NOT_NULL:
            return value is not None

        # Si la valeur est None et qu'on n'est pas dans un test de nullité
        if value is None:
            return False

        # Opérateurs de comparaison
        if op == ConditionOperator.EQUALS:
            return value == cond_value
        if op == ConditionOperator.NOT_EQUALS:
            return value != cond_value
        if op == ConditionOperator.GREATER_THAN:
            return float(value) > float(cond_value)
        if op == ConditionOperator.GREATER_THAN_OR_EQUAL:
            return float(value) >= float(cond_value)
        if op == ConditionOperator.LESS_THAN:
            return float(value) < float(cond_value)
        if op == ConditionOperator.LESS_THAN_OR_EQUAL:
            return float(value) <= float(cond_value)

        # Opérateurs de chaîne
        if op == ConditionOperator.CONTAINS:
            return str(cond_value) in str(value)
        if op == ConditionOperator.NOT_CONTAINS:
            return str(cond_value) not in str(value)
        if op == ConditionOperator.REGEX:
            return bool(re.search(str(cond_value), str(value)))

        # Opérateurs d'appartenance
        if op == ConditionOperator.IN:
            if isinstance(cond_value, list):
                return value in cond_value
            return str(value) in str(cond_value).split(",")
        if op == ConditionOperator.NOT_IN:
            if isinstance(cond_value, list):
                return value not in cond_value
            return str(value) not in str(cond_value).split(",")

        return False


class InputNode(BaseNode):
    """
    Nœud d'entrée : lit un champ de la vulnérabilité.
    Config attendue: {"field": "cvss_score"}

    Supports virtual CVSS fields (cvss_av, cvss_ac, etc.) that are parsed
    from the cvss_vector field on demand.
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        field = self.config.get("field")
        if not field:
            raise NodeEvaluationError(f"Nœud {self.id}: champ 'field' non configuré")

        # Récupère la valeur du champ
        vuln_data = context.get("vulnerability", {})
        value = vuln_data.get(field)

        # Cherche aussi dans extra si pas trouvé
        if value is None and "extra" in vuln_data:
            value = vuln_data["extra"].get(field)

        # Handle virtual CVSS fields (cvss_av, cvss_ac, etc.)
        if value is None:
            from app.engine.cvss import is_cvss_field, parse_cvss_vector

            if is_cvss_field(field):
                cvss_vector = vuln_data.get("cvss_vector")
                if cvss_vector is None and "extra" in vuln_data:
                    cvss_vector = vuln_data["extra"].get("cvss_vector")
                if cvss_vector:
                    parsed = parse_cvss_vector(cvss_vector)
                    value = parsed.get(field)

        # Trouve la condition qui matche
        match = self.match_condition(value)
        if match is None:
            # Pas de condition matchée, on continue avec default si configuré
            default_idx = self.config.get("default_branch")
            if default_idx is not None and default_idx < len(self.conditions):
                return value, self.conditions[default_idx].label
            raise NodeEvaluationError(
                f"Nœud {self.id}: aucune condition ne correspond à la valeur '{value}'"
            )

        return value, match[1]


class LookupNode(BaseNode):
    """
    Nœud lookup : recherche une valeur dans une table externe (ex: assets).

    Config:
    {
        "lookup_table": "assets",
        "lookup_key": "asset_id",
        "lookup_field": "criticality"
    }
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        lookup_table = self.config.get("lookup_table")
        lookup_key = self.config.get("lookup_key")
        lookup_field = self.config.get("lookup_field")

        if not all([lookup_table, lookup_key, lookup_field]):
            raise NodeEvaluationError(
                f"Nœud {self.id}: configuration lookup incomplète"
            )

        # Récupère la clé de lookup depuis la vulnérabilité
        vuln_data = context.get("vulnerability", {})
        key_value = vuln_data.get(lookup_key) or vuln_data.get("extra", {}).get(lookup_key)

        if key_value is None:
            # Pas de clé, on utilise la branche default si configurée
            default_idx = self.config.get("default_branch")
            if default_idx is not None:
                return None, self.conditions[default_idx].label if self.conditions else None
            raise NodeEvaluationError(
                f"Nœud {self.id}: clé de lookup '{lookup_key}' non trouvée"
            )

        # Cherche dans le cache de lookup du contexte
        lookup_cache = context.get("lookups", {}).get(lookup_table, {})
        lookup_result = lookup_cache.get(str(key_value))

        if lookup_result is None:
            default_idx = self.config.get("default_branch")
            if default_idx is not None:
                return None, self.conditions[default_idx].label if self.conditions else None
            raise NodeEvaluationError(
                f"Nœud {self.id}: asset '{key_value}' non trouvé dans {lookup_table}"
            )

        # Extrait le champ demandé
        value = lookup_result.get(lookup_field)

        match = self.match_condition(value)
        if match is None:
            raise NodeEvaluationError(
                f"Nœud {self.id}: aucune condition ne correspond à '{value}'"
            )

        return value, match[1]


class OutputNode(BaseNode):
    """
    Nœud de sortie : retourne la décision finale.
    Config attendue: {"decision": "Act", "color": "#ff0000"}
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        decision = self.config.get("decision", "Unknown")
        return decision, None


def create_node(schema: NodeSchema) -> BaseNode:
    """Factory pour créer le bon type de nœud selon le schéma."""
    node_classes = {
        NodeType.INPUT: InputNode,
        NodeType.LOOKUP: LookupNode,
        NodeType.OUTPUT: OutputNode,
    }

    node_class = node_classes.get(schema.type)
    if not node_class:
        raise ValueError(f"Type de nœud inconnu: {schema.type}")

    return node_class(schema)
