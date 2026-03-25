"""Sanitization of uploaded filenames.

Standalone module (no dependency on settings / DB) so it can be
tested and imported anywhere.
"""

import os
import re

# Maximum filename length after sanitization
MAX_FILENAME_LENGTH = 255


def sanitize_filename(filename: str | None) -> str | None:
    """Sanitize an uploaded filename to prevent injections.

    - Extracts only the basename (removes path traversal)
    - Removes null and control characters
    - Removes dangerous special characters
    - Truncates to MAX_FILENAME_LENGTH characters
    - Returns None if the result is empty
    """
    if not filename:
        return None

    # Remove null and control characters (U+0000 to U+001F, U+007F)
    name = re.sub(r"[\x00-\x1f\x7f]", "", filename)

    # Normalize Windows path separators to Unix, then extract basename
    name = name.replace("\\", "/")
    name = os.path.basename(name)

    # Remove dangerous characters for file systems and HTTP headers
    name = re.sub(r'[<>:"|?*]', "", name)

    # Remove leading dots (hidden files, traversal ..)
    name = name.lstrip(".")

    # Truncate to maximum length
    name = name[:MAX_FILENAME_LENGTH]

    return name.strip() or None
