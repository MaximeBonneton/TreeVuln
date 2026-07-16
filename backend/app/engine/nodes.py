"""
Definition of node types and their evaluation logic.
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
    """Error during node evaluation."""

    pass


# ReDoS protection: length limit and timeout for user-provided regex
_REGEX_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_MAX_REGEX_PATTERN_LENGTH = 200
_REGEX_TIMEOUT_SECONDS = 1.0


def _safe_regex_match(pattern: str, text: str) -> bool:
    """Execute a regex match with length limit and timeout (prevents ReDoS)."""
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
    """Base class for all node types."""

    def __init__(self, schema: NodeSchema):
        self.id = schema.id
        self.label = schema.label
        self.type = schema.type
        self.config = schema.config
        self.conditions = schema.conditions

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> tuple[Any, int | None, str | None]:
        """
        Evaluate the node with the given context.

        Args:
            context: Dictionary containing vulnerability data
                     and lookup results.

        Returns:
            Tuple (evaluated_value, matched_condition_index, matched_condition_label).
            E-5: condition_index is returned directly by the node so the
            inference engine never needs to re-derive it by searching for a
            matching label (which breaks when two conditions share a label).
            For an OUTPUT node, returns (decision, None, None).
        """
        pass

    def match_condition(
        self, value: Any, context: dict[str, Any] | None = None
    ) -> tuple[int, str] | None:
        """
        Find the condition that matches the value.

        Args:
            value: Main value to evaluate
            context: Full context (needed for compound conditions
                     that may reference other fields)

        Returns:
            Tuple (condition_index, condition_label) or None if no match.
        """
        for idx, condition in enumerate(self.conditions):
            if self._evaluate_condition(value, condition, context or {}):
                return idx, condition.label
        return None

    def _get_field_value(self, context: dict[str, Any], field: str) -> Any:
        """
        Retrieve a field value from the context.

        Args:
            context: Evaluation context containing vulnerability and lookups
            field: Field name to retrieve

        Returns:
            Field value or None if not found
        """
        vuln_data = context.get("vulnerability", {})
        value = vuln_data.get(field)

        # Search in extra if not found
        if value is None and "extra" in vuln_data:
            value = vuln_data["extra"].get(field)

        # Handle virtual CVSS fields
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
        Evaluate a simple condition (operator + value).

        Args:
            value: Value to test
            op: Comparison operator
            cond_value: Reference value

        Returns:
            True if the condition is satisfied
        """
        # Handle null values
        if op == ConditionOperator.IS_NULL:
            return value is None
        if op == ConditionOperator.IS_NOT_NULL:
            return value is not None

        # If value is None and we're not in a null test
        if value is None:
            return False

        # Comparison operators
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

        # String operators
        if op == ConditionOperator.CONTAINS:
            return str(cond_value) in str(value)
        if op == ConditionOperator.NOT_CONTAINS:
            return str(cond_value) not in str(value)
        if op == ConditionOperator.REGEX:
            return _safe_regex_match(str(cond_value), str(value))

        # Membership operators
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
        Evaluate a simple criterion of a compound condition.

        Args:
            criterion: The criterion to evaluate
            default_value: Default value (main field of the node)
            context: Evaluation context

        Returns:
            True if the criterion is satisfied
        """
        # If a field is specified, read it from context
        # Otherwise use the default value of the node
        if criterion.field is not None:
            value = self._get_field_value(context, criterion.field)
        else:
            value = default_value

        return self._evaluate_simple(value, criterion.operator, criterion.value)

    def _evaluate_condition(
        self, value: Any, condition: NodeCondition, context: dict[str, Any]
    ) -> bool:
        """
        Evaluate whether a value satisfies a condition.

        Supports two modes:
        - Simple mode: operator + value (backward compatible)
        - Compound mode: logic (AND/OR) + criteria

        Args:
            value: Main value to test
            condition: Condition to evaluate
            context: Full context (for additional fields in compound mode)

        Returns:
            True if the condition is satisfied
        """
        # Compound mode (AND/OR with multiple criteria)
        if condition.logic is not None and condition.criteria:
            results = [
                self._evaluate_criterion(criterion, value, context)
                for criterion in condition.criteria
            ]

            if condition.logic == "AND":
                return all(results)
            else:  # OR
                return any(results)

        # Simple mode (backward compatible)
        if condition.operator is not None:
            return self._evaluate_simple(value, condition.operator, condition.value)

        # Fallback (should not happen with Pydantic validation)
        return False


class InputNode(BaseNode):
    """
    Input node: reads a field from the vulnerability.
    Expected config: {"field": "cvss_score"}

    Supports virtual CVSS fields (cvss_av, cvss_ac, etc.) that are parsed
    from the cvss_vector field on demand.
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, int | None, str | None]:
        field = self.config.get("field")
        if not field:
            raise NodeEvaluationError(f"Node {self.id}: field 'field' not configured")

        # Retrieve field value via _get_field_value
        value = self._get_field_value(context, field)

        # Find matching condition (pass context for compound conditions)
        match = self.match_condition(value, context)
        if match is None:
            # No matching condition, continue with default if configured
            default_idx = self.config.get("default_branch")
            if default_idx is not None and default_idx < len(self.conditions):
                return value, default_idx, self.conditions[default_idx].label
            raise NodeEvaluationError(
                f"Node {self.id}: no condition matches value '{value}'"
            )

        # E-5: on renvoie l'index de la condition matchée tel que trouvé par
        # match_condition, pour que l'engine route sans avoir à re-dériver
        # cet index en recherchant le label (ambigu si labels dupliqués).
        return value, match[0], match[1]


class LookupNode(BaseNode):
    """
    Lookup node: searches for a value in an external table (e.g. assets).

    Config:
    {
        "lookup_table": "assets",
        "lookup_key": "asset_id",
        "lookup_field": "criticality"
    }
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, int | None, str | None]:
        lookup_table = self.config.get("lookup_table")
        lookup_key = self.config.get("lookup_key")
        lookup_field = self.config.get("lookup_field")

        if not all([lookup_table, lookup_key, lookup_field]):
            raise NodeEvaluationError(
                f"Node {self.id}: incomplete lookup configuration"
            )

        # Retrieve lookup key from the vulnerability
        vuln_data = context.get("vulnerability", {})
        key_value = vuln_data.get(lookup_key) or vuln_data.get("extra", {}).get(lookup_key)

        if key_value is None:
            # No key, use the default branch if configured
            default_idx = self.config.get("default_branch")
            if default_idx is not None:
                condition_index = default_idx if self.conditions else None
                label = self.conditions[default_idx].label if self.conditions else None
                return None, condition_index, label
            raise NodeEvaluationError(
                f"Node {self.id}: lookup key '{lookup_key}' not found"
            )

        # Search in the lookup cache from context
        lookup_cache = context.get("lookups", {}).get(lookup_table, {})
        lookup_result = lookup_cache.get(str(key_value))

        if lookup_result is None:
            default_idx = self.config.get("default_branch")
            if default_idx is not None:
                condition_index = default_idx if self.conditions else None
                label = self.conditions[default_idx].label if self.conditions else None
                return None, condition_index, label
            raise NodeEvaluationError(
                f"Node {self.id}: asset '{key_value}' not found in {lookup_table}"
            )

        # Extract the requested field
        value = lookup_result.get(lookup_field)

        # Pass context for compound conditions
        match = self.match_condition(value, context)
        if match is None:
            raise NodeEvaluationError(
                f"Node {self.id}: no condition matches '{value}'"
            )

        return value, match[0], match[1]


class EquationNode(BaseNode):
    """
    Equation node: computes a score from a multi-field formula.

    Expected config:
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
        Apply text-to-number mapping tables to variables.

        For each variable with a configured value_map:
        - If the raw value is a string, searches in entries and
          replaces with the numeric value (or default_value if not found)
        - If the value is None, uses default_value
        - Numeric/boolean values pass through as-is
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

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, int | None, str | None]:
        from app.engine.formula import FormulaError, evaluate_formula

        formula = self.config.get("formula")
        if not formula:
            raise NodeEvaluationError(f"Node {self.id}: formula not configured")

        variable_names = self.config.get("variables", [])

        # Collect variable values from context
        variables: dict[str, Any] = {}
        for var_name in variable_names:
            value = self._get_field_value(context, var_name)
            variables[var_name] = value

        # Apply text-to-number mappings if configured
        value_maps = self.config.get("value_maps", {})
        if value_maps:
            variables = self._apply_value_maps(variables, value_maps)

        # Evaluate the formula
        try:
            score = evaluate_formula(formula, variables)
        except FormulaError as e:
            raise NodeEvaluationError(f"Node {self.id}: {e}") from e

        # Route by thresholds via the existing condition system
        match = self.match_condition(score, context)
        if match is None:
            default_idx = self.config.get("default_branch")
            if default_idx is not None and default_idx < len(self.conditions):
                return score, default_idx, self.conditions[default_idx].label
            raise NodeEvaluationError(
                f"Node {self.id}: no condition matches score {score}"
            )

        return score, match[0], match[1]


class OutputNode(BaseNode):
    """
    Output node: returns the final decision.
    Expected config: {"decision": "Act", "color": "#ff0000"}
    """

    def evaluate(self, context: dict[str, Any]) -> tuple[Any, int | None, str | None]:
        decision = self.config.get("decision", "Unknown")
        return decision, None, None


def create_node(schema: NodeSchema) -> BaseNode:
    """Factory to create the correct node type from the schema."""
    node_classes = {
        NodeType.INPUT: InputNode,
        NodeType.LOOKUP: LookupNode,
        NodeType.EQUATION: EquationNode,
        NodeType.OUTPUT: OutputNode,
    }

    node_class = node_classes.get(schema.type)
    if not node_class:
        raise ValueError(f"Unknown node type: {schema.type}")

    return node_class(schema)
