"""Routes des settings globaux (CSAF : identité éditeur + clé de signature)."""
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SettingsServiceDep, require_role
from app.crypto import encrypt_secret
from app.schemas.settings import (
    CsafPublisher,
    CsafSettingsResponse,
    CsafSettingsUpdate,
)
from app.services.csaf_signing import SigningError, get_key_fingerprint
from app.services.settings_service import CSAF_SETTINGS_KEY

router = APIRouter()


def _to_response(stored: dict[str, Any] | None) -> CsafSettingsResponse:
    if not stored:
        return CsafSettingsResponse()
    publisher = stored.get("publisher")
    return CsafSettingsResponse(
        publisher=CsafPublisher.model_validate(publisher) if publisher else None,
        has_signing_key=bool(stored.get("signing_key")),
        signing_key_fingerprint=stored.get("signing_key_fingerprint"),
    )


@router.get("/csaf", response_model=CsafSettingsResponse)
async def get_csaf_settings(settings_service: SettingsServiceDep):
    """Settings CSAF courants (sans secret). Accessible à tout utilisateur
    authentifié : le TestPanel en a besoin pour l'état du bouton d'export."""
    stored = await settings_service.get_setting(CSAF_SETTINGS_KEY)
    return _to_response(stored)


@router.put("/csaf", response_model=CsafSettingsResponse)
async def update_csaf_settings(
    payload: CsafSettingsUpdate,
    settings_service: SettingsServiceDep,
    _=require_role("admin"),
):
    """Met à jour partiellement les settings CSAF (admin uniquement)."""
    stored = await settings_service.get_setting(CSAF_SETTINGS_KEY) or {}

    if payload.publisher is not None:
        stored["publisher"] = payload.publisher.model_dump()

    if payload.remove_signing_key:
        stored.pop("signing_key", None)
        stored.pop("signing_key_passphrase", None)
        stored.pop("signing_key_fingerprint", None)
    elif payload.signing_key is not None:
        try:
            fingerprint = get_key_fingerprint(payload.signing_key)
        except SigningError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OpenPGP private key",
            )
        stored["signing_key"] = encrypt_secret(payload.signing_key)
        stored["signing_key_passphrase"] = (
            encrypt_secret(payload.signing_key_passphrase)
            if payload.signing_key_passphrase
            else None
        )
        stored["signing_key_fingerprint"] = fingerprint

    await settings_service.set_setting(CSAF_SETTINGS_KEY, stored)
    return _to_response(stored)
