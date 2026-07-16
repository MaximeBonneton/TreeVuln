"""
Tests de sécurité pour le moteur de formules (formula.py).

Vérifie que l'AST validator rejette toutes les constructions dangereuses
et que les chemins positifs fonctionnent correctement.
"""

import pytest

from app.engine.formula import (
    FormulaError,
    evaluate_formula,
    extract_variables,
    validate_formula,
)


# ======================================================================
# Tests de sécurité — constructions qui DOIVENT être rejetées
# ======================================================================


class TestFormulaSecurityImport:
    """Tentatives d'import de modules."""

    def test_reject_import(self):
        with pytest.raises(FormulaError):
            validate_formula("__import__('os').system('id')")

    def test_reject_import_in_eval(self):
        with pytest.raises(FormulaError):
            evaluate_formula("__import__('os')", {})

    def test_reject_importlib(self):
        with pytest.raises(FormulaError):
            validate_formula("__import__('importlib').import_module('os')")


class TestFormulaSecurityBuiltins:
    """Tentatives d'accès aux builtins dangereux."""

    def test_reject_open(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("open('/etc/passwd')")

    def test_reject_exec(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("exec('print(1)')")

    def test_reject_eval_call(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("eval('1+1')")

    def test_reject_compile(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("compile('1', '', 'eval')")

    def test_reject_print(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("print(1)")

    def test_reject_type(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("type(1)")

    def test_reject_getattr(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("getattr(x, '__class__')", ["x"])

    def test_reject_setattr(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("setattr(x, 'y', 1)", ["x"])

    def test_reject_delattr(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("delattr(x, 'y')", ["x"])

    def test_reject_globals(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("globals()")

    def test_reject_locals(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("locals()")

    def test_reject_dir(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("dir()")

    def test_reject_vars(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("vars()")

    def test_reject_input(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("input()")

    def test_reject_breakpoint(self):
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("breakpoint()")


class TestFormulaSecurityAttributeAccess:
    """Tentatives d'accès aux attributs (class, bases, subclasses, etc.)."""

    def test_reject_attribute_access(self):
        with pytest.raises(FormulaError, match="Unauthorized construct"):
            validate_formula("x.__class__", ["x"])

    def test_reject_class_bases(self):
        with pytest.raises(FormulaError):
            validate_formula("().__class__.__bases__[0]")

    def test_reject_subclasses(self):
        with pytest.raises(FormulaError):
            validate_formula("().__class__.__bases__[0].__subclasses__()")

    def test_reject_mro(self):
        with pytest.raises(FormulaError):
            validate_formula("x.__class__.__mro__", ["x"])

    def test_reject_dict_access(self):
        with pytest.raises(FormulaError):
            validate_formula("x.__dict__", ["x"])

    def test_reject_module_access(self):
        with pytest.raises(FormulaError):
            validate_formula("x.__module__", ["x"])

    def test_reject_globals_attr(self):
        with pytest.raises(FormulaError):
            validate_formula("x.__globals__", ["x"])


class TestFormulaSecurityStringLiterals:
    """Les littéraux chaîne doivent être rejetés (pourraient servir d'injection)."""

    def test_reject_string_literal(self):
        with pytest.raises(FormulaError, match="Unauthorized literal type"):
            validate_formula("'hello'")

    def test_reject_string_in_expression(self):
        with pytest.raises(FormulaError):
            validate_formula("x + 'exploit'", ["x"])

    def test_reject_fstring_attempt(self):
        """Les f-strings ne sont pas valides dans eval mode de toute façon."""
        with pytest.raises(FormulaError):
            validate_formula("f'{x}'", ["x"])

    def test_reject_bytes_literal(self):
        with pytest.raises(FormulaError):
            validate_formula("b'hello'")


class TestFormulaSecurityComprehensions:
    """List/dict/set comprehensions et generators."""

    def test_reject_list_comprehension(self):
        with pytest.raises(FormulaError, match="Unauthorized construct"):
            validate_formula("[x for x in range(10)]")

    def test_reject_dict_comprehension(self):
        with pytest.raises(FormulaError):
            validate_formula("{x: x for x in range(10)}")

    def test_reject_set_comprehension(self):
        with pytest.raises(FormulaError):
            validate_formula("{x for x in range(10)}")

    def test_reject_generator(self):
        with pytest.raises(FormulaError):
            validate_formula("sum(x for x in range(10))")


class TestFormulaSecurityLambdaAndDef:
    """Lambda et définition de fonctions."""

    def test_reject_lambda(self):
        with pytest.raises(FormulaError):
            validate_formula("(lambda: 1)()")

    def test_reject_lambda_with_args(self):
        with pytest.raises(FormulaError):
            validate_formula("(lambda x: x * 2)(5)")


class TestFormulaSecuritySubscript:
    """Accès par index (empêche l'accès à __subclasses__()[N], etc.)."""

    def test_reject_subscript(self):
        with pytest.raises(FormulaError, match="Unauthorized construct"):
            validate_formula("x[0]", ["x"])

    def test_reject_slice(self):
        with pytest.raises(FormulaError):
            validate_formula("x[0:5]", ["x"])


class TestFormulaSecurityDataStructures:
    """Création de listes, dicts, sets, tuples."""

    def test_reject_list_literal(self):
        with pytest.raises(FormulaError, match="Unauthorized construct"):
            validate_formula("[1, 2, 3]")

    def test_reject_dict_literal(self):
        with pytest.raises(FormulaError):
            validate_formula("{'a': 1}")

    def test_reject_set_literal(self):
        with pytest.raises(FormulaError):
            validate_formula("{1, 2, 3}")

    def test_reject_tuple_in_call(self):
        """Tuple via la fonction tuple() doit être rejeté."""
        with pytest.raises(FormulaError, match="not allowed"):
            validate_formula("tuple()")


class TestFormulaSecurityKeywordArgs:
    """Arguments nommés dans les fonctions autorisées."""

    def test_reject_keyword_args(self):
        with pytest.raises(FormulaError, match="Named arguments"):
            validate_formula("round(x, ndigits=2)", ["x"])


class TestFormulaSecurityMethodCalls:
    """Appels de méthodes (obj.method())."""

    def test_reject_method_call(self):
        with pytest.raises(FormulaError, match="simple function calls"):
            validate_formula("x.upper()", ["x"])

    def test_reject_chained_method(self):
        with pytest.raises(FormulaError):
            validate_formula("x.y.z()", ["x"])


class TestFormulaSecurityStarExpressions:
    """Expressions * et **."""

    def test_reject_starred(self):
        with pytest.raises(FormulaError):
            validate_formula("max(*x)", ["x"])


# ======================================================================
# Tests fonctionnels — chemins positifs
# ======================================================================


class TestFormulaBasicArithmetic:
    """Opérations arithmétiques de base."""

    def test_addition(self):
        assert evaluate_formula("x + y", {"x": 3, "y": 4}) == 7.0

    def test_subtraction(self):
        assert evaluate_formula("x - y", {"x": 10, "y": 3}) == 7.0

    def test_multiplication(self):
        assert evaluate_formula("x * y", {"x": 3, "y": 4}) == 12.0

    def test_division(self):
        assert evaluate_formula("x / y", {"x": 10, "y": 4}) == 2.5

    def test_floor_division(self):
        assert evaluate_formula("x // y", {"x": 10, "y": 3}) == 3.0

    def test_modulo(self):
        assert evaluate_formula("x % y", {"x": 10, "y": 3}) == 1.0

    def test_power(self):
        assert evaluate_formula("x ** 2", {"x": 5}) == 25.0

    def test_unary_minus(self):
        assert evaluate_formula("-x", {"x": 5}) == -5.0

    def test_complex_expression(self):
        result = evaluate_formula("(x + y) * 2 - z", {"x": 3, "y": 4, "z": 1})
        assert result == 13.0

    def test_numeric_literal(self):
        assert evaluate_formula("x + 10", {"x": 5}) == 15.0

    def test_float_literal(self):
        assert evaluate_formula("x * 0.5", {"x": 10}) == 5.0


class TestFormulaComparisons:
    """Comparaisons et opérateurs booléens."""

    def test_greater_than_true(self):
        assert evaluate_formula("x > 5", {"x": 10}) == 1.0

    def test_greater_than_false(self):
        assert evaluate_formula("x > 5", {"x": 3}) == 0.0

    def test_less_than(self):
        assert evaluate_formula("x < 5", {"x": 3}) == 1.0

    def test_equality(self):
        assert evaluate_formula("x == 5", {"x": 5}) == 1.0

    def test_not_equal(self):
        assert evaluate_formula("x != 5", {"x": 3}) == 1.0

    def test_and_operator(self):
        assert evaluate_formula("x > 0 and y > 0", {"x": 1, "y": 1}) == 1.0

    def test_or_operator(self):
        assert evaluate_formula("x > 0 or y > 0", {"x": -1, "y": 1}) == 1.0

    def test_not_operator(self):
        assert evaluate_formula("not x", {"x": 0}) == 1.0


class TestFormulaTernary:
    """Expressions ternaires (C-style et Python-style)."""

    def test_ternary_c_style_true(self):
        result = evaluate_formula("(x > 5) ? 10 : 0", {"x": 8})
        assert result == 10.0

    def test_ternary_c_style_false(self):
        result = evaluate_formula("(x > 5) ? 10 : 0", {"x": 3})
        assert result == 0.0

    def test_ternary_simple(self):
        result = evaluate_formula("x ? 1 : 0", {"x": 5})
        assert result == 1.0


class TestFormulaFunctions:
    """Fonctions autorisées : min, max, abs, round."""

    def test_min(self):
        assert evaluate_formula("min(x, y)", {"x": 3, "y": 7}) == 3.0

    def test_max(self):
        assert evaluate_formula("max(x, y)", {"x": 3, "y": 7}) == 7.0

    def test_abs_positive(self):
        assert evaluate_formula("abs(x)", {"x": -5}) == 5.0

    def test_abs_negative(self):
        assert evaluate_formula("abs(x)", {"x": 5}) == 5.0

    def test_round(self):
        assert evaluate_formula("round(x)", {"x": 3.7}) == 4.0

    def test_nested_functions(self):
        result = evaluate_formula("max(min(x, 10), 0)", {"x": 15})
        assert result == 10.0

    def test_function_with_arithmetic(self):
        result = evaluate_formula("abs(x - y) * 2", {"x": 3, "y": 8})
        assert result == 10.0


class TestFormulaVariableExtraction:
    """Extraction et validation des variables."""

    def test_extract_simple(self):
        variables = extract_variables("x + y")
        assert set(variables) == {"x", "y"}

    def test_extract_with_functions(self):
        variables = extract_variables("min(x, max(y, z))")
        assert set(variables) == {"x", "y", "z"}

    def test_extract_no_duplicates(self):
        variables = extract_variables("x + x + x")
        assert variables == ["x"]

    def test_validate_unknown_variable(self):
        with pytest.raises(FormulaError, match="Unknown variables"):
            validate_formula("x + y + z", available_variables=["x", "y"])


class TestFormulaEdgeCases:
    """Cas limites et erreurs."""

    def test_empty_formula(self):
        with pytest.raises(FormulaError, match="empty"):
            validate_formula("")

    def test_whitespace_formula(self):
        with pytest.raises(FormulaError, match="empty"):
            validate_formula("   ")

    def test_division_by_zero(self):
        with pytest.raises(FormulaError, match="Division by zero"):
            evaluate_formula("x / 0", {"x": 1})

    def test_none_variable(self):
        with pytest.raises(FormulaError, match="None"):
            evaluate_formula("x + 1", {"x": None})

    def test_string_variable_numeric(self):
        """Les chaînes numériques sont converties en float."""
        assert evaluate_formula("x + 1", {"x": "5"}) == 6.0

    def test_string_variable_non_numeric(self):
        with pytest.raises(FormulaError, match="cannot be converted to a number"):
            evaluate_formula("x + 1", {"x": "abc"})

    def test_bool_variable_true(self):
        assert evaluate_formula("x + 1", {"x": True}) == 2.0

    def test_bool_variable_false(self):
        assert evaluate_formula("x + 1", {"x": False}) == 1.0

    def test_syntax_error(self):
        with pytest.raises(FormulaError, match="Syntax error"):
            validate_formula("x +* y")

    def test_unsupported_type_variable(self):
        with pytest.raises(FormulaError, match="unsupported type"):
            evaluate_formula("x + 1", {"x": [1, 2]})


class TestFormulaRealisticSSVC:
    """Formules réalistes du contexte SSVC."""

    def test_weighted_risk_score(self):
        result = evaluate_formula(
            "cvss_score * 0.4 + epss_score * 100 * 0.6",
            {"cvss_score": 9.8, "epss_score": 0.7},
        )
        assert abs(result - (9.8 * 0.4 + 70 * 0.6)) < 0.001

    def test_priority_with_ternary(self):
        result = evaluate_formula(
            "(kev > 0) ? cvss_score * 2 : cvss_score",
            {"kev": 1, "cvss_score": 7.5},
        )
        assert result == 15.0

    def test_clamped_score(self):
        result = evaluate_formula(
            "min(max(cvss_score + epss_score * 3, 0), 10)",
            {"cvss_score": 8.5, "epss_score": 0.9},
        )
        assert result == 10.0


# ======================================================================
# S-13a — bornage de l'opérateur puissance (DoS via entiers gigantesques)
# ======================================================================


class TestFormulaSecurityPowerBound:
    """
    Un utilisateur authentifié (y compris rôle operator) contrôle la
    formule d'un arbre via les endpoints preview/diagnose. Sans bornage,
    une formule comme `9**9**9**9` (associativité à droite : 9**(9**(9**9)))
    produit un entier de plusieurs milliards de chiffres et gèle/OOM le
    worker sur une seule requête.
    """

    def test_reject_chained_power_dos(self):
        """Le cas emblématique du DoS doit être rejeté AVANT tout calcul géant."""
        with pytest.raises(FormulaError):
            evaluate_formula("9**9**9**9", {})

    def test_reject_large_literal_exponent(self):
        with pytest.raises(FormulaError, match="Exponent"):
            evaluate_formula("2 ** 100", {})

    def test_reject_large_variable_exponent(self):
        """La base et l'exposant peuvent être des variables : le bornage
        doit s'appliquer aux VALEURS au moment de l'évaluation, pas
        seulement à l'AST statique."""
        with pytest.raises(FormulaError, match="Exponent"):
            evaluate_formula("x ** y", {"x": 2, "y": 999999})

    def test_reject_when_result_magnitude_too_large(self):
        """Revue 2026-07-16 #3 : la borne porte sur la magnitude estimée du
        résultat (|exp| × log10(|base|)), pas sur la base seule."""
        with pytest.raises(FormulaError, match="result"):
            evaluate_formula("x ** 8", {"x": 1e50})

    def test_reject_large_literal_result(self):
        with pytest.raises(FormulaError, match="result"):
            evaluate_formula("1e50 ** 8", {})

    def test_small_power_still_works(self):
        """Les formules métier légitimes (score^2, score^3) restent valides."""
        assert evaluate_formula("x ** 2", {"x": 5}) == 25.0
        assert evaluate_formula("x ** 3", {"x": 2}) == 8.0

    def test_negative_exponent_within_bound(self):
        assert evaluate_formula("x ** -1", {"x": 4}) == 0.25

    def test_power_at_exponent_threshold(self):
        """Exposant exactement à la limite autorisée : doit passer."""
        assert evaluate_formula("2 ** 8", {}) == 256.0

    def test_power_just_above_threshold_rejected(self):
        with pytest.raises(FormulaError, match="Exponent"):
            evaluate_formula("2 ** 9", {})

    def test_nested_power_within_bounds(self):
        """Puissance imbriquée mais dont chaque étage reste sous les seuils."""
        # 2**2 = 4, puis 4**2 = 16 : chaque étage est individuellement borné.
        assert evaluate_formula("(2 ** 2) ** 2", {}) == 16.0


# ======================================================================
# Revue 2026-07-16 (WS3-R Task 3) — reprises S-13a
# ======================================================================


class TestPowerBoundLargeBaseNonRegression:
    """
    Revue #3 : l'ancienne borne rejetait |base| > 1_000_000 quel que soit
    l'exposant, cassant des formules métier légitimes sur des champs à
    grande valeur (timestamp epoch, compteurs) alors qu'aucune explosion
    n'est possible pour un petit exposant.
    """

    def test_epoch_timestamp_squared_is_allowed(self):
        assert evaluate_formula("x ** 2", {"x": 1_700_000_000}) == pytest.approx(
            2.89e18, rel=1e-6
        )

    def test_large_base_exponent_one_is_allowed(self):
        assert evaluate_formula("x ** 1", {"x": 1_700_000_000}) == 1_700_000_000.0

    def test_large_base_exponent_zero_is_allowed(self):
        assert evaluate_formula("x ** 0", {"x": 1e300}) == 1.0


class TestPowerBoundAtSaveTime:
    """
    Revue #4 : validate_formula est appelée à la sauvegarde de l'arbre
    (tree_validation.py) mais ignorait les bornes de `**` : un arbre se
    sauvegardait sans avertissement puis échouait à CHAQUE évaluation.
    Les opérandes constantes doivent être bornées dès la validation.
    """

    def test_validate_rejects_large_constant_exponent(self):
        with pytest.raises(FormulaError, match="Exponent"):
            validate_formula("2 ** 999")

    def test_validate_rejects_negative_large_exponent(self):
        with pytest.raises(FormulaError, match="Exponent"):
            validate_formula("2 ** -999")

    def test_validate_rejects_chained_power_dos(self):
        with pytest.raises(FormulaError):
            validate_formula("9**9**9**9")

    def test_validate_rejects_large_constant_result(self):
        with pytest.raises(FormulaError, match="result"):
            validate_formula("1e50 ** 8")

    def test_validate_accepts_variable_power(self):
        # Opérandes variables : contrôlables uniquement à l'exécution
        assert validate_formula("x ** y") == ["x", "y"]

    def test_validate_accepts_small_constant_power(self):
        assert validate_formula("score ** 2") == ["score"]


class TestReservedVariableNames:
    """
    Revue #5 : une variable de formule littéralement nommée `_safe_pow`
    masquait la fonction injectée dans les locals d'eval (LOAD_NAME résout
    les locals avant les globals), transformant tout `**` en
    « 'float' object is not callable ». Les noms commençant par `_` sont
    réservés au moteur.
    """

    def test_variable_shadowing_safe_pow_is_rejected(self):
        with pytest.raises(FormulaError, match="reserved"):
            evaluate_formula("x ** 2", {"x": 3, "_safe_pow": 5})

    def test_underscore_name_in_formula_rejected_at_validation(self):
        with pytest.raises(FormulaError, match="reserved"):
            validate_formula("_safe_pow + 1")

    def test_underscore_name_in_formula_rejected_at_evaluation(self):
        with pytest.raises(FormulaError, match="reserved"):
            evaluate_formula("_hidden + 1", {"_hidden": 1})

    def test_normal_power_still_works(self):
        assert evaluate_formula("x ** 2", {"x": 3}) == 9.0
