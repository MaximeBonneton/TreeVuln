"""Schemas Pydantic des settings CSAF (identité éditeur + clé de signature)."""
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CsafPublisher(BaseModel):
    """Identité éditeur CSAF (document.publisher)."""

    name: str = Field(min_length=1, max_length=255)
    namespace: str = Field(description="URL de namespace de l'éditeur")
    category: Literal[
        "vendor", "coordinator", "discoverer", "other", "translator", "user"
    ] = "vendor"

    @field_validator("namespace")
    @classmethod
    def namespace_est_une_url(cls, v: str) -> str:
        # HttpUrl normalise (ajoute un / final...) : on valide sans transformer
        HttpUrl(v)
        return v


class CsafSettingsUpdate(BaseModel):
    """Mise à jour partielle des settings CSAF (PUT).

    Chaque champ absent est conservé tel quel. remove_signing_key=True
    supprime la clé (prioritaire sur signing_key).
    """

    publisher: CsafPublisher | None = None
    signing_key: str | None = Field(
        default=None, description="Clé privée OpenPGP armored (write-only)"
    )
    signing_key_passphrase: str | None = None
    remove_signing_key: bool = False


class CsafSettingsResponse(BaseModel):
    """Settings CSAF exposés — jamais la clé privée ni la passphrase."""

    publisher: CsafPublisher | None = None
    has_signing_key: bool = False
    signing_key_fingerprint: str | None = None
