"""
Secure formula evaluator based on the ast module.

Parses formulas into Python AST and only evaluates allowed constructs:
- Numeric literals, variables, arithmetic operators (+, -, *, /, **, %)
- Comparisons, ternary (condition ? val_true : val_false)
- Functions: min(), max(), abs(), round()
"""

import ast
import re
from typing import Any


class FormulaError(Exception):
    """Error during formula validation or evaluation."""

    pass


# Allowed functions in formulas
_ALLOWED_FUNCTIONS = {"min", "max", "abs", "round"}

# S-13a : bornage de l'opérateur puissance (**) pour éviter un DoS.
# Une formule comme "9**9**9**9" est évaluée de droite à gauche par Python
# (9**(9**(9**9))) et produit un entier de plusieurs milliards de chiffres :
# calcul qui gèle le worker (CPU) et peut faire OOM le process, pour une
# seule requête d'un utilisateur authentifié (même rôle operator, via les
# endpoints preview/diagnose qui contrôlent la formule ET les variables).
# Les formules métier légitimes (scores de risque : cvss*poids, epss*100,
# score^2, score^3...) n'utilisent que des exposants petits (<= 8) et des
# bases raisonnables (<= 1_000_000) : ces seuils sont donc très larges pour
# l'usage réel tout en empêchant la construction de grands entiers.
_MAX_POWER_EXPONENT = 8
_MAX_POWER_BASE = 1_000_000

# Regex to convert C-style ternary syntax to Python
# condition ? val_true : val_false  ->  (val_true if condition else val_false)
_TERNARY_RE = re.compile(
    r"""
    \(([^?()]+)\)   # group 1: condition in parentheses
    \s*\?\s*        # ?
    ([^:]+?)        # group 2: val_true
    \s*:\s*         # :
    ([^)]+?)        # group 3: val_false
    (?=\s*[+\-*/%),]|\s*$)  # followed by an operator, closing, or end
    """,
    re.VERBOSE,
)

# Simplified version without parentheses around the condition
_TERNARY_SIMPLE_RE = re.compile(
    r"""
    ([a-zA-Z_][a-zA-Z0-9_]*(?:\s*[><=!]+\s*[\w.]+)?)  # condition simple
    \s*\?\s*        # ?
    ([^:]+?)        # val_true
    \s*:\s*         # :
    ([^),]+?)       # val_false
    (?=\s*[+\-*/%),]|\s*$)
    """,
    re.VERBOSE,
)


def _preprocess_formula(formula: str) -> str:
    """Convert C-style ternary syntax to Python."""
    result = formula

    # Replace parenthesized ternaries: (cond) ? a : b -> (a if cond else b)
    def replace_paren_ternary(m: re.Match) -> str:
        cond, val_true, val_false = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        return f"({val_true} if {cond} else {val_false})"

    result = _TERNARY_RE.sub(replace_paren_ternary, result)

    # Replace simple ternaries: var ? a : b -> (a if var else b)
    def replace_simple_ternary(m: re.Match) -> str:
        cond, val_true, val_false = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        return f"({val_true} if {cond} else {val_false})"

    result = _TERNARY_SIMPLE_RE.sub(replace_simple_ternary, result)

    return result


def _safe_pow(base: float, exponent: float) -> float:
    """
    Calcule `base ** exponent` en bornant les deux opérandes (S-13a).

    Une whitelist statique sur l'AST (cf. `_validate_node`) ne suffit pas :
    la base et l'exposant peuvent être des variables dont la valeur n'est
    connue qu'à l'exécution (ex: `x ** y` avec y=999999 fourni en entrée).
    Le bornage doit donc s'appliquer aux VALEURS, au moment du calcul.

    Raises:
        FormulaError: si l'exposant ou la base dépassent les seuils
            autorisés (empêche la construction d'entiers gigantesques).
    """
    if abs(exponent) > _MAX_POWER_EXPONENT:
        raise FormulaError(
            f"Exponent too large ({exponent}): must not exceed "
            f"{_MAX_POWER_EXPONENT} in absolute value"
        )
    if abs(base) > _MAX_POWER_BASE:
        raise FormulaError(
            f"Base too large ({base}): must not exceed {_MAX_POWER_BASE} in absolute value"
        )
    return base**exponent


class _PowerBoundTransformer(ast.NodeTransformer):
    """
    Remplace chaque opération `**` de l'AST par un appel à `_safe_pow`
    (S-13a), afin que la borne soit appliquée à l'exécution, y compris
    pour les puissances imbriquées (ex: `9**9**9**9`), qui sont visitées
    et donc bornées de l'intérieur vers l'extérieur (l'étage le plus
    profond est calculé -- et potentiellement rejeté -- en premier, avant
    même que Python n'essaie de calculer l'étage suivant).
    """

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if isinstance(node.op, ast.Pow):
            call = ast.Call(
                func=ast.Name(id="_safe_pow", ctx=ast.Load()),
                args=[node.left, node.right],
                keywords=[],
            )
            return ast.copy_location(call, node)
        return node


def _validate_node(node: ast.AST) -> None:
    """Recursively validate an AST node. Raises FormulaError if forbidden."""
    # Numeric and boolean literals
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, bool)):
            raise FormulaError(f"Unauthorized literal type: {type(node.value).__name__}")
        return

    # Variables (names)
    if isinstance(node, ast.Name):
        return

    # Unary operations (-, +, not)
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, (ast.UAdd, ast.USub, ast.Not)):
            raise FormulaError(f"Unauthorized unary operator: {type(node.op).__name__}")
        _validate_node(node.operand)
        return

    # Binary operations (+, -, *, /, **, %, //)
    if isinstance(node, ast.BinOp):
        allowed_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
        if not isinstance(node.op, allowed_ops):
            raise FormulaError(f"Unauthorized binary operator: {type(node.op).__name__}")
        _validate_node(node.left)
        _validate_node(node.right)
        return

    # Comparisons (<, >, <=, >=, ==, !=)
    if isinstance(node, ast.Compare):
        allowed_cmp = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
        for op in node.ops:
            if not isinstance(op, allowed_cmp):
                raise FormulaError(f"Unauthorized comparison operator: {type(op).__name__}")
        _validate_node(node.left)
        for comparator in node.comparators:
            _validate_node(comparator)
        return

    # Boolean operations (and, or)
    if isinstance(node, ast.BoolOp):
        for value in node.values:
            _validate_node(value)
        return

    # Ternary (val_true if condition else val_false)
    if isinstance(node, ast.IfExp):
        _validate_node(node.test)
        _validate_node(node.body)
        _validate_node(node.orelse)
        return

    # Function calls (min, max, abs, round only)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaError("Only simple function calls are allowed")
        if node.func.id not in _ALLOWED_FUNCTIONS:
            raise FormulaError(
                f"Function '{node.func.id}' not allowed. "
                f"Available functions: {', '.join(sorted(_ALLOWED_FUNCTIONS))}"
            )
        if node.keywords:
            raise FormulaError("Named arguments are not allowed in functions")
        for arg in node.args:
            _validate_node(arg)
        return

    # Expression wrapper (top-level)
    if isinstance(node, ast.Expression):
        _validate_node(node.body)
        return

    # Everything else is forbidden
    raise FormulaError(
        f"Unauthorized construct in formula: {type(node).__name__}. "
        "Only literals, variables, arithmetic operators, comparisons, "
        "ternaries and min/max/abs/round functions are allowed."
    )


def extract_variables(formula: str) -> list[str]:
    """
    Extract variable names from a formula.

    Args:
        formula: The formula to analyze

    Returns:
        List of variable names (deduplicated, in order of appearance)
    """
    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError:
        # Fallback: extraction by regex
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", formula)
        seen: set[str] = set()
        result: list[str] = []
        for t in tokens:
            if t not in _ALLOWED_FUNCTIONS and t not in ("if", "else", "and", "or", "not", "True", "False") and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    variables: list[str] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in _ALLOWED_FUNCTIONS:
            if node.id not in seen:
                seen.add(node.id)
                variables.append(node.id)

    return variables


def validate_formula(formula: str, available_variables: list[str] | None = None) -> list[str]:
    """
    Validate formula syntax and return used variables.

    Args:
        formula: The formula to validate
        available_variables: If provided, verifies that variables are in this list

    Returns:
        List of used variables

    Raises:
        FormulaError: If the formula is invalid
    """
    if not formula or not formula.strip():
        raise FormulaError("Formula cannot be empty")

    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Syntax error in formula: {e}") from e

    _validate_node(tree)

    variables = extract_variables(formula)

    if available_variables is not None:
        unknown = [v for v in variables if v not in available_variables]
        if unknown:
            raise FormulaError(
                f"Unknown variables: {', '.join(unknown)}. "
                f"Available variables: {', '.join(available_variables)}"
            )

    return variables


def evaluate_formula(formula: str, variables: dict[str, Any]) -> float:
    """
    Evaluate a formula with the provided variables.

    Args:
        formula: The formula to evaluate
        variables: Dictionary {variable_name: value}

    Returns:
        Numeric result (float)

    Raises:
        FormulaError: If evaluation fails
    """
    if not formula or not formula.strip():
        raise FormulaError("Formula cannot be empty")

    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Syntax error in formula: {e}") from e

    _validate_node(tree)

    # S-13a : transforme `**` en appel borné `_safe_pow` avant compilation.
    # Appliqué APRÈS la validation statique (qui rejette déjà tout appel
    # explicite à `_safe_pow` car hors de `_ALLOWED_FUNCTIONS`), donc un
    # utilisateur ne peut pas contourner le bornage en appelant la fonction
    # lui-même.
    tree = _PowerBoundTransformer().visit(tree)
    ast.fix_missing_locations(tree)

    # Prepare variables: coerce booleans to float, reject None
    safe_vars: dict[str, float] = {}
    for name, value in variables.items():
        if value is None:
            raise FormulaError(
                f"Variable '{name}' is None. "
                "All variables must have a value to evaluate the formula."
            )
        if isinstance(value, bool):
            safe_vars[name] = 1.0 if value else 0.0
        elif isinstance(value, (int, float)):
            safe_vars[name] = float(value)
        elif isinstance(value, str):
            try:
                safe_vars[name] = float(value)
            except ValueError:
                raise FormulaError(
                    f"Variable '{name}' has value '{value}' which cannot be converted to a number"
                )
        else:
            raise FormulaError(
                f"Variable '{name}' has unsupported type: {type(value).__name__}"
            )

    # Restricted execution environment
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_globals["min"] = min
    safe_globals["max"] = max
    safe_globals["abs"] = abs
    safe_globals["round"] = round
    safe_globals["True"] = True
    safe_globals["False"] = False
    safe_globals["_safe_pow"] = _safe_pow

    compiled = compile(tree, "<formula>", "eval")

    try:
        result = eval(compiled, safe_globals, safe_vars)  # noqa: S307
    except ZeroDivisionError:
        raise FormulaError("Division by zero in formula")
    except Exception as e:
        raise FormulaError(f"Evaluation error: {e}") from e

    if isinstance(result, bool):
        return 1.0 if result else 0.0

    try:
        return float(result)
    except (TypeError, ValueError) as e:
        raise FormulaError(f"Formula result is not a number: {result}") from e
