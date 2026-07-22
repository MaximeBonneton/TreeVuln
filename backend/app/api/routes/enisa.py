"""Routes REST des événements de notification ENISA (Phase 3 CRA).

L'authentification (session valide) est appliquée au niveau du routeur
(cf. `app/api/__init__.py`, `dependencies=RequireAuth`) : ces routes sont
accessibles à tout utilisateur authentifié (admin ou operator), sans
restriction de rôle supplémentaire.
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select

from app.api.deps import DBSession, RequireAuth, SettingsServiceDep
from app.engine.enisa import (
    MILESTONES,
    build_milestone_content,
    compute_milestones,
    merge_draft,
    render_markdown,
)
from app.models.enisa import EnisaEvent
from app.schemas.enisa import (
    CloseRequest,
    CorrectiveDateRequest,
    DismissRequest,
    DraftUpdateRequest,
    EnisaEventDetail,
    EnisaEventListResponse,
    EnisaEventSummary,
    EnisaSummaryResponse,
    MilestoneState,
)
from app.services.settings_service import ENISA_SETTINGS_KEY

router = APIRouter()

Milestone = Literal["early_warning", "notification", "final_report"]

_SUBMITTED_AT = {
    "early_warning": "early_warning_submitted_at",
    "notification": "notification_submitted_at",
    "final_report": "final_report_submitted_at",
}
_SUBMITTED_BY = {
    "early_warning": "early_warning_submitted_by",
    "notification": "notification_submitted_by",
    "final_report": "final_report_submitted_by",
}


async def _get_event(db: DBSession, event_id: int) -> EnisaEvent:
    event = await db.get(EnisaEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="ENISA event not found")
    return event


def _with_milestones(event: EnisaEvent, model: type):
    """Sérialise l'événement puis calcule les échéances des jalons (non stockées)."""
    now = datetime.now(timezone.utc)
    data = model.model_validate(event)
    data.milestones = {
        name: MilestoneState(**state)
        for name, state in compute_milestones(event, now).items()
    }
    return data


@router.get("/events", response_model=EnisaEventListResponse)
async def list_events(
    db: DBSession,
    tree_id: int,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Liste paginée des événements d'un arbre, échéances calculées."""
    query = select(EnisaEvent).where(EnisaEvent.tree_id == tree_id)
    count_query = select(func.count()).select_from(EnisaEvent).where(
        EnisaEvent.tree_id == tree_id
    )
    if status_filter:
        query = query.where(EnisaEvent.status == status_filter)
        count_query = count_query.where(EnisaEvent.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    rows = await db.execute(
        query.order_by(EnisaEvent.last_detected_at.desc()).limit(limit).offset(offset)
    )
    events = [_with_milestones(e, EnisaEventSummary) for e in rows.scalars().all()]
    return EnisaEventListResponse(events=events, total=total)


@router.get("/events/{event_id}", response_model=EnisaEventDetail)
async def get_event(db: DBSession, event_id: int):
    event = await _get_event(db, event_id)
    return _with_milestones(event, EnisaEventDetail)


@router.post("/events/{event_id}/confirm", response_model=EnisaEventDetail)
async def confirm_event(db: DBSession, user: RequireAuth, event_id: int):
    """candidate -> confirmed : pose la prise de connaissance (ancre du chrono)."""
    event = await _get_event(db, event_id)
    if event.status != "candidate":
        raise HTTPException(status_code=409, detail=f"Cannot confirm from '{event.status}'")
    event.status = "confirmed"
    event.confirmed_at = datetime.now(timezone.utc)
    event.confirmed_by = user.username
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.post("/events/{event_id}/dismiss", response_model=EnisaEventDetail)
async def dismiss_event(
    db: DBSession, user: RequireAuth, event_id: int, payload: DismissRequest
):
    event = await _get_event(db, event_id)
    if event.status != "candidate":
        raise HTTPException(status_code=409, detail=f"Cannot dismiss from '{event.status}'")
    event.status = "dismissed"
    event.dismissed_at = datetime.now(timezone.utc)
    event.dismissed_by = user.username
    event.dismiss_reason = payload.reason
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.post("/events/{event_id}/reopen", response_model=EnisaEventDetail)
async def reopen_event(db: DBSession, event_id: int):
    """dismissed -> candidate (réouverture manuelle uniquement)."""
    event = await _get_event(db, event_id)
    if event.status != "dismissed":
        raise HTTPException(status_code=409, detail=f"Cannot reopen from '{event.status}'")
    event.status = "candidate"
    event.dismissed_at = None
    event.dismiss_reason = None
    event.dismissed_by = None
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.post("/events/{event_id}/close", response_model=EnisaEventDetail)
async def close_event(db: DBSession, event_id: int, payload: CloseRequest):
    """confirmed -> closed : libre si 3 jalons soumis, sinon motif obligatoire."""
    event = await _get_event(db, event_id)
    if event.status != "confirmed":
        raise HTTPException(status_code=409, detail=f"Cannot close from '{event.status}'")
    all_submitted = all(
        getattr(event, _SUBMITTED_AT[m]) is not None for m in MILESTONES
    )
    if not all_submitted and not payload.reason:
        raise HTTPException(
            status_code=409,
            detail="Closing with unsubmitted milestones requires a reason",
        )
    event.status = "closed"
    event.closed_at = datetime.now(timezone.utc)
    event.close_reason = payload.reason
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.post("/events/{event_id}/submit/{milestone}", response_model=EnisaEventDetail)
async def submit_milestone(
    db: DBSession, user: RequireAuth, event_id: int, milestone: Milestone
):
    """Marque un jalon comme soumis sur la plateforme ENISA (manuel, tracé)."""
    event = await _get_event(db, event_id)
    if event.status != "confirmed":
        raise HTTPException(status_code=409, detail=f"Cannot submit from '{event.status}'")
    setattr(event, _SUBMITTED_AT[milestone], datetime.now(timezone.utc))
    setattr(event, _SUBMITTED_BY[milestone], user.username)
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.put("/events/{event_id}/draft/{milestone}", response_model=EnisaEventDetail)
async def update_draft(
    db: DBSession, event_id: int, milestone: Milestone, payload: DraftUpdateRequest
):
    event = await _get_event(db, event_id)
    drafts = dict(event.drafts or {})
    drafts[milestone] = payload.fields
    event.drafts = drafts
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.put("/events/{event_id}/corrective-date", response_model=EnisaEventDetail)
async def set_corrective_date(
    db: DBSession, event_id: int, payload: CorrectiveDateRequest
):
    event = await _get_event(db, event_id)
    event.corrective_available_at = payload.corrective_available_at
    await db.commit()
    await db.refresh(event)
    return _with_milestones(event, EnisaEventDetail)


@router.get("/events/{event_id}/export/{milestone}")
async def export_milestone(
    db: DBSession,
    settings_service: SettingsServiceDep,
    event_id: int,
    milestone: Milestone,
    format: Literal["json", "markdown"] = "json",
):
    """Export du jalon : pré-rempli fusionné aux brouillons."""
    event = await _get_event(db, event_id)
    enisa_settings = await settings_service.get_setting(ENISA_SETTINGS_KEY) or {}
    prefilled = build_milestone_content(event, milestone, enisa_settings)
    content = merge_draft(prefilled, (event.drafts or {}).get(milestone, {}))
    if format == "markdown":
        return PlainTextResponse(render_markdown(content, milestone))
    return content


@router.get("/summary", response_model=EnisaSummaryResponse)
async def get_summary(db: DBSession, tree_id: int):
    """Compteurs pour les badges UI."""
    rows = await db.execute(
        select(EnisaEvent).where(
            EnisaEvent.tree_id == tree_id,
            EnisaEvent.status.in_(["candidate", "confirmed"]),
        )
    )
    now = datetime.now(timezone.utc)
    candidates = confirmed = overdue = 0
    for event in rows.scalars().all():
        if event.status == "candidate":
            candidates += 1
        else:
            confirmed += 1
            milestones = compute_milestones(event, now)
            overdue += sum(1 for m in milestones.values() if m["overdue"])
    return EnisaSummaryResponse(
        candidates=candidates, confirmed=confirmed, overdue_milestones=overdue
    )
