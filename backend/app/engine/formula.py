"""
Évaluateur de formules sécurisé basé sur le module ast.

Parse les formules en AST Python et n'évalue que les constructions autorisées :
- Littéraux numériques, variables, opérateurs arithmétiques (+, -, *, /, **, %)
- Comparaisons, ternaire (condition ? val_true : val_false)
- Fonctions : min(), max(), abs(), round()
"""

import ast
import re
from typing import Any


class FormulaError(Exception):
    """Erreur lors de la validation ou l'évaluation d'une formule."""

    pass


# Fonctions autorisées dans les formules
_ALLOWED_FUNCTIONS = {"min", "max", "abs", "round"}

# Regex pour convertir la syntaxe ternaire C-style en Python
# condition ? val_true : val_false  ->  (val_true if condition else val_false)
_TERNARY_RE = re.compile(
    r"""
    \(([^?()]+)\)   # groupe 1 : condition entre parenthèses
    \s*\?\s*        # ?
    ([^:]+?)        # groupe 2 : val_true
    \s*:\s*         # :
    ([^)]+?)        # groupe 3 : val_false
    (?=\s*[+\-*/%),]|\s*$)  # suivi d'un opérateur, fermeture, ou fin
    """,
    re.VERBOSE,
)

# Version simplifiée sans parenthèses autour de la condition
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
    """Convertit la syntaxe ternaire C-style en Python."""
    result = formula

    # Remplace les ternaires avec parenthèses : (cond) ? a : b -> (a if cond else b)
    def replace_paren_ternary(m: re.Match) -> str:
        cond, val_true, val_false = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        return f"({val_true} if {cond} else {val_false})"

    result = _TERNARY_RE.sub(replace_paren_ternary, result)

    # Remplace les ternaires simples : var ? a : b -> (a if var else b)
    def replace_simple_ternary(m: re.Match) -> str:
        cond, val_true, val_false = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        return f"({val_true} if {cond} else {val_false})"

    result = _TERNARY_SIMPLE_RE.sub(replace_simple_ternary, result)

    return result


def _validate_node(node: ast.AST) -> None:
    """Valide récursivement un noeud AST. Lève FormulaError si interdit."""
    # Littéraux numériques et booléens
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, bool)):
            raise FormulaError(f"Type de littéral non autorisé : {type(node.value).__name__}")
        return

    # Variables
    if isinstance(node, ast.Name):
        return

    # Opérations unaires (-, +, not)
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, (ast.UAdd, ast.USub, ast.Not)):
            raise FormulaError(f"Opérateur unaire non autorisé : {type(node.op).__name__}")
        _validate_node(node.operand)
        return

    # Opérations binaires (+, -, *, /, **, %, //)
    if isinstance(node, ast.BinOp):
        allowed_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
        if not isinstance(node.op, allowed_ops):
            raise FormulaError(f"Opérateur binaire non autorisé : {type(node.op).__name__}")
        _validate_node(node.left)
        _validate_node(node.right)
        return

    # Comparaisons (<, >, <=, >=, ==, !=)
    if isinstance(node, ast.Compare):
        allowed_cmp = (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq)
        for op in node.ops:
            if not isinstance(op, allowed_cmp):
                raise FormulaError(f"Opérateur de comparaison non autorisé : {type(op).__name__}")
        _validate_node(node.left)
        for comparator in node.comparators:
            _validate_node(comparator)
        return

    # Opérations booléennes (and, or)
    if isinstance(node, ast.BoolOp):
        for value in node.values:
            _validate_node(value)
        return

    # Ternaire (val_true if condition else val_false)
    if isinstance(node, ast.IfExp):
        _validate_node(node.test)
        _validate_node(node.body)
        _validate_node(node.orelse)
        return

    # Appels de fonctions (min, max, abs, round uniquement)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaError("Seuls les appels de fonctions simples sont autorisés")
        if node.func.id not in _ALLOWED_FUNCTIONS:
            raise FormulaError(
                f"Fonction '{node.func.id}' non autorisée. "
                f"Fonctions disponibles : {', '.join(sorted(_ALLOWED_FUNCTIONS))}"
            )
        if node.keywords:
            raise FormulaError("Les arguments nommés ne sont pas autorisés dans les fonctions")
        for arg in node.args:
            _validate_node(arg)
        return

    # Expression wrapper
    if isinstance(node, ast.Expression):
        _validate_node(node.body)
        return

    # Tout le reste est interdit
    raise FormulaError(
        f"Construction non autorisée dans la formule : {type(node).__name__}. "
        "Seuls les littéraux, variables, opérateurs arithmétiques, comparaisons, "
        "ternaires et fonctions min/max/abs/round sont autorisés."
    )


def extract_variables(formula: str) -> list[str]:
    """
    Extrait les noms de variables d'une formule.

    Args:
        formula: La formule à analyser

    Returns:
        Liste des noms de variables (dédupliquée, ordre d'apparition)
    """
    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError:
        # Fallback : extraction par regex
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
    Valide la syntaxe d'une formule et retourne les variables utilisées.

    Args:
        formula: La formule à valider
        available_variables: Si fourni, vérifie que les variables sont dans cette liste

    Returns:
        Liste des variables utilisées

    Raises:
        FormulaError: Si la formule est invalide
    """
    if not formula or not formula.strip():
        raise FormulaError("La formule ne peut pas être vide")

    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Erreur de syntaxe dans la formule : {e}") from e

    _validate_node(tree)

    variables = extract_variables(formula)

    if available_variables is not None:
        unknown = [v for v in variables if v not in available_variables]
        if unknown:
            raise FormulaError(
                f"Variables inconnues : {', '.join(unknown)}. "
                f"Variables disponibles : {', '.join(available_variables)}"
            )

    return variables


def evaluate_formula(formula: str, variables: dict[str, Any]) -> float:
    """
    Évalue une formule avec les variables fournies.

    Args:
        formula: La formule à évaluer
        variables: Dictionnaire {nom_variable: valeur}

    Returns:
        Résultat numérique (float)

    Raises:
        FormulaError: Si l'évaluation échoue
    """
    if not formula or not formula.strip():
        raise FormulaError("La formule ne peut pas être vide")

    preprocessed = _preprocess_formula(formula)

    try:
        tree = ast.parse(preprocessed, mode="eval")
    except SyntaxError as e:
        raise FormulaError(f"Erreur de syntaxe dans la formule : {e}") from e

    _validate_node(tree)

    # Prépare les variables : coerce booleans en float, rejette None
    safe_vars: dict[str, float] = {}
    for name, value in variables.items():
        if value is None:
            raise FormulaError(
                f"La variable '{name}' est None. "
                "Toutes les variables doivent avoir une valeur pour évaluer la formule."
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
                    f"La variable '{name}' a la valeur '{value}' qui ne peut pas être convertie en nombre"
                )
        else:
            raise FormulaError(
                f"La variable '{name}' a un type non supporté : {type(value).__name__}"
            )

    # Environnement d'exécution restreint
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    safe_globals["min"] = min
    safe_globals["max"] = max
    safe_globals["abs"] = abs
    safe_globals["round"] = round
    safe_globals["True"] = True
    safe_globals["False"] = False

    compiled = compile(tree, "<formula>", "eval")

    try:
        result = eval(compiled, safe_globals, safe_vars)  # noqa: S307
    except ZeroDivisionError:
        raise FormulaError("Division par zéro dans la formule")
    except Exception as e:
        raise FormulaError(f"Erreur d'évaluation : {e}") from e

    if isinstance(result, bool):
        return 1.0 if result else 0.0

    try:
        return float(result)
    except (TypeError, ValueError) as e:
        raise FormulaError(f"Le résultat de la formule n'est pas un nombre : {result}") from e
