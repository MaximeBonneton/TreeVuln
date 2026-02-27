"""Sanitisation des noms de fichiers uploadés.

Module autonome (sans dépendance aux settings / DB) pour pouvoir être
testé et importé partout.
"""

import os
import re

# Longueur maximale d'un nom de fichier après sanitisation
MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str | None) -> str | None:
    """Nettoie un nom de fichier uploadé pour empêcher les injections.

    - Extrait uniquement le basename (supprime les chemins de traversée)
    - Supprime les caractères nuls et de contrôle
    - Supprime les caractères spéciaux dangereux
    - Tronque à MAX_FILENAME_LENGTH caractères
    - Retourne None si le résultat est vide
    """
    if not filename:
        return None

    # Supprime les caractères nuls et de contrôle (U+0000 à U+001F, U+007F)
    name = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # Normalise les séparateurs de chemin Windows → Unix, puis extrait le basename
    name = name.replace("\\", "/")
    name = os.path.basename(name)

    # Supprime les caractères dangereux pour les systèmes de fichiers et les headers HTTP
    name = re.sub(r'[<>:"|?*]', "", name)

    # Supprime les points en début de nom (fichiers cachés, traversée ..)
    name = name.lstrip(".")

    # Tronque à la longueur maximale
    name = name[:MAX_FILENAME_LENGTH]

    return name.strip() or None
