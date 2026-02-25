"""
Définition des types de nœuds et de leur logique d'évaluation.
"""

import concurrent.futures
import re
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.tree import (
    ConditionOperator,
    NodeCondition,
    NodeSchema,
    NodeType,
    SimpleConditionCriteria,
)


class NodeEvaluationError(Exception):
    """Erreur lors de l'évaluation d'un nœud."""

    pass


# Protection ReDoS : limite de longueur et timeout pour les regex utilisateur
_REGEX_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_MAX_REGEX_PATTERN_LENGTH = 200
_REGEX_TIMEOUT_SECONDS = 1.0


def _safe_regex_match(pattern: str, text: str) -> bool:
    """Exécute un match regex avec limite de longueur et timeout (prévient les ReDoS)."""
    if len(pattern) > _MAX_REGEX_PATTERN_LENGTH:
        return False
    try:
        compiled = re.compile(pattern)
    except re.error:
        return False
    future = _REGEX_EXECUTOR.submit(compiled.search, text)
    try:
        return bool(future.result(timeout=_REGEX_TIMEOUT_SECONDS))
    except (concurrent.futures.TimeoutError, Exception):
        return False


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

    def match_condition(
        self, value: Any, context: dict[str, Any] | None = None
    ) -> tuple[int, str] | None:
        """
        Trouve la condition qui correspond à la valeur.

        Args:
            value: Valeur principale à évaluer
            context: Contexte complet (nécessaire pour les conditions composées
                     qui peuvent référencer d'autres champs)

        Returns:
            Tuple (index_condition, label_condition) ou None si aucune ne matche.
        """
        for idx, condition in enumerate(self.conditions):
            if self._evaluate_condition(value, condition, context or {}):
                return idx, condition.label
        return None

    def _get_field_value(self, context: dict[str, Any], field: str) -> Any:
        """
        Récupère la valeur d'un champ depuis le contexte.

        Args:
            context: Contexte d'évaluation contenant vulnerability et lookups
            field: Nom du champ à récupérer

        Returns:
            Valeur du champ ou None si non trouvé
        """
        vuln_data = context.get("vulnerability", {})
        value = vuln_data.get(field)

        # Cherche dans extra si pas trouvé
        if value is None and "extra" in vuln_data:
            value = vuln_data["extra"].get(field)

        # Gère les champs CVSS virtuels
        if value is None:
            from app.engine.cvss import is_cvss_field, parse_cvss_vector

            if is_cvss_field(field):
                cvss_vector = vuln_data.get("cvss_vector")
                if cvss_vector is None and "extra" in vuln_data:
                    cvss_vector = vuln_data["extra"].get("cvss_vector")
                if cvss_vector:
                    parsed = parse_cvss_vector(cvss_vector)
                    value = parsed.get(field)

        return value

    def _evaluate_simple(
        self, value: Any, op: ConditionOperator, cond_value: Any
    ) -> bool:
        """
        Évalue une condition simple (opérateur + valeur).

        Args:
            value: Valeur à tester
            op: Opérateur de comparaison
            cond_value: Valeur de référence

        Returns:
            True si la condition est satisfaite
        """
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
            return _safe_regex_match(str(cond_value), str(value))

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

    def _evaluate_criterion(
        self,
        criterion: SimpleConditionCriteria,
        default_value: Any,
        context: dict[str, Any],
    ) -> bool:
        """
        Évalue un critère simple d'une condition composée.

        Args:
            criterion: Le critère à évaluer
            default_value: Valeur par défaut (champ principal du nœud)
            context: Contexte d'évaluation

        Returns:
            True si le critère est satisfait
        """
        # Si un champ est spécifié, on le lit depuis le contexte
        # Sinon on utilise la valeur par défaut du nœud
        if criterion.field is not None:
            value = self._get_field_value(context, criterion.field)
        else:
            value = default_value

        return self._evaluate_simple(value, criterion.operator, criterion.value)

    def _evaluate_condition(
        self, value: Any, condition: NodeCondition, context: dict[str, Any]
    ) -> bool:
        """
        Évalue si une valeur satisfait une condition.

        Supporte deux modes :
        - Mode simple : operator + value (rétrocompatible)
        - Mode composé : logic (AND/OR) + criteria

        Args:
            value: Valeur principale à tester
            condition: Condition à évaluer
            context: Contexte complet (pour les champs additionnels en mode composé)

        Returns:
            True si la condition est satisfaite
        """
        # Mode composé (AND/OR avec critères multiples)
        if condition.logic is not None and condition.criteria:
            results = [
                self._evaluate_criterion(criterion, value, context)
                for criterion in condition.criteria
            ]

            if condition.logic == "AND":
                return all(results)
            else:  # OR
                return any(results)

        # Mode simple (rétrocompatible)
        if condition.operator is not None:
            return self._evaluate_simple(value, condition.operator, condition.value)

        # Fallback (ne devrait pas arriver avec la validation Pydantic)
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

        # Récupère la valeur du champ via _get_field_value
        value = self._get_field_value(context, field)

        # Trouve la condition qui matche (passe le contexte pour les conditions composées)
        match = self.match_condition(value, context)
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

        # Passe le contexte pour les conditions composées
        match = self.match_condition(value, context)
        if match is None:
            raise NodeEvaluationError(
                f"Nœud {self.id}: aucune condition ne correspond à '{value}'"
            )

        return value, match[1]


class EquationNode(BaseNode):
    """
    Nœud équation : calcule un score à partir d'une formule multi-champs.

    Config attendue:
    {
        "formula": "cvss_score * 0.4 + epss_score * 100 * 0.3 + (kev ? 30 : 0)",
        "variables": ["cvss_score", "epss_score", "kev"],
        "output_label": "Risk Score"
    }
    """

    @staticmethod
    def _apply_value_maps(
        variables: dict[str, Any], value_maps: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Applique les tables de mapping texte → nombre aux variables.

        Pour chaque variable ayant un value_map configuré :
        - Si la valeur brute est une chaîne, cherche dans les entries et
          remplace par la valeur numérique (ou default_value si non trouvé)
        - Si la valeur est None, utilise default_value
        - Les valeurs numériques/booléennes passent telles quelles
        """
        for var_name, vmap in value_maps.items():
            if var_name not in variables:
                continue

            entries = vmap.get("entries", [])
            default_value = vmap.get("default_value", 0)
            raw = variables[var_name]

            if raw is None:
                variables[var_name] = default_value
            elif isinstance(raw, str):
                matched = False
                for entry in entries:
                    if entry.get("text") == raw:
                        variables[var_name] = entry.get("value", default_value)
                        matched = True
                        break
                if not matched:
                    variables[var_name] = default_value

        return variables

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, str | None]:
        from app.engine.formula import FormulaError, evaluate_formula

        formula = self.config.get("formula")
        if not formula:
            raise NodeEvaluationError(f"Nœud {self.id}: formule non configurée")

        variable_names = self.config.get("variables", [])

        # Collecte les valeurs des variables depuis le contexte
        variables: dict[str, Any] = {}
        for var_name in variable_names:
            value = self._get_field_value(context, var_name)
            variables[var_name] = value

        # Applique les mappings texte → nombre si configurés
        value_maps = self.config.get("value_maps", {})
        if value_maps:
            variables = self._apply_value_maps(variables, value_maps)

        # Évalue la formule
        try:
            score = evaluate_formula(formula, variables)
        except FormulaError as e:
            raise NodeEvaluationError(f"Nœud {self.id}: {e}") from e

        # Route par seuils via le système de conditions existant
        match = self.match_condition(score, context)
        if match is None:
            default_idx = self.config.get("default_branch")
            if default_idx is not None and default_idx < len(self.conditions):
                return score, self.conditions[default_idx].label
            raise NodeEvaluationError(
                f"Nœud {self.id}: aucune condition ne correspond au score {score}"
            )

        return score, match[1]


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
        NodeType.EQUATION: EquationNode,
        NodeType.OUTPUT: OutputNode,
    }

    node_class = node_classes.get(schema.type)
    if not node_class:
        raise ValueError(f"Type de nœud inconnu: {schema.type}")

    return node_class(schema)
