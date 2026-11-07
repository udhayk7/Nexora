import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.networking import (
    FollowUpDueResponse,
    NetworkingActivityResponse,
    NetworkingContactCreateRequest,
    NetworkingContactResponse,
    NetworkingContactUpdateRequest,
    NetworkingCRMOverviewResponse,
    OutreachApproveRequest,
    OutreachGenerateRequest,
    OutreachMessageResponse,
    OutreachSendGmailRequest,
    RecruiterCreateRequest,
    RecruiterDiscoveryResponse,
    RecruiterProfileResponse,
    RecruiterUpdateRequest,
)
from app.services.networking_crm_service import NetworkingCRMService
from app.services.recruiter_discovery_service import RecruiterDiscoveryService
from app.services.recruiter_matching_engine import RecruiterMatchingEngine

logger = logging.getLogger("nexora.api.networking")

router = APIRouter(prefix="/networking", tags=["Professional Networking & Recruiter Intelligence"])


# ---------------------------------------------------------------------------
# 1. Recruiter Discovery & Intelligence
# ---------------------------------------------------------------------------


@router.get(
    "/recruiters",
    response_model=RecruiterDiscoveryResponse,
    summary="Discover and rank relevant recruiters",
    description=(
        "Lists and ranks recruiters matching candidate skills, target roles, "
        "and preferred companies with explainable recommendations."
    ),
)
def discover_recruiters(
    query: Optional[str] = Query(None, description="Search by name, company, or specialization"),
    company_id: Optional[uuid.UUID] = Query(None, description="Filter by company"),
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    verification_status: Optional[str] = Query(None, description="verified, inferred, unverified"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecruiterDiscoveryResponse:
    recruiters, total = RecruiterDiscoveryService.list_recruiters(
        db=db,
        user=current_user,
        query=query,
        company_id=company_id,
        specialization=specialization,
        verification_status=verification_status,
        limit=limit,
        offset=offset,
    )

    # Rank and explain matches
    matched_items = RecruiterMatchingEngine.match_and_rank_recruiters(
        db=db,
        user=current_user,
        recruiters=recruiters,
    )

    verified_count = sum(1 for r in recruiters if r.verification_status == "verified")
    companies_count = len({r.company_id for r in recruiters if r.company_id})

    return RecruiterDiscoveryResponse(
        total=total,
        items=matched_items,
        verified_count=verified_count,
        companies_count=companies_count,
    )


@router.post(
    "/recruiters",
    response_model=RecruiterProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a recruiter profile",
    description=(
        "Allows candidates to manually record recruiter intelligence with duplicate prevention."
    ),
)
def create_recruiter(
    payload: RecruiterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecruiterProfileResponse:
    recruiter = RecruiterDiscoveryService.create_recruiter_profile(
        db=db,
        user=current_user,
        data=payload,
    )
    return RecruiterProfileResponse.model_validate(recruiter)


@router.get(
    "/recruiters/{recruiter_id}",
    response_model=RecruiterProfileResponse,
    summary="Get recruiter profile details",
)
def get_recruiter(
    recruiter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecruiterProfileResponse:
    recruiter = RecruiterDiscoveryService.get_recruiter_by_id(db, recruiter_id)
    return RecruiterProfileResponse.model_validate(recruiter)


@router.patch(
    "/recruiters/{recruiter_id}",
    response_model=RecruiterProfileResponse,
    summary="Update recruiter profile",
)
def update_recruiter(
    recruiter_id: uuid.UUID,
    payload: RecruiterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecruiterProfileResponse:
    recruiter = RecruiterDiscoveryService.update_recruiter_profile(
        db=db,
        user=current_user,
        recruiter_id=recruiter_id,
        data=payload,
    )
    return RecruiterProfileResponse.model_validate(recruiter)


@router.post(
    "/recruiters/discover-company/{company_id}",
    response_model=list[RecruiterProfileResponse],
    summary="Discover company recruitment contacts",
    description="Scans verified company jobs and sources to discover hiring contacts.",
)
def discover_company_recruiters(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RecruiterProfileResponse]:
    discovered = RecruiterDiscoveryService.discover_and_seed_company_recruiters(
        db=db,
        company_id=company_id,
    )
    return [RecruiterProfileResponse.model_validate(r) for r in discovered]


# ---------------------------------------------------------------------------
# 2. Networking CRM Management
# ---------------------------------------------------------------------------


@router.get(
    "/crm/overview",
    response_model=NetworkingCRMOverviewResponse,
    summary="Get candidate Networking CRM dashboard",
    description=(
        "Aggregated relationship KPIs, tracked companies, response stats, and contact list."
    ),
)
def get_crm_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NetworkingCRMOverviewResponse:
    return NetworkingCRMService.get_crm_overview(db=db, user=current_user)


@router.post(
    "/crm/contacts",
    response_model=NetworkingContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add recruiter to Networking CRM",
    description="Establishes a networking relationship record. Prevents duplicates.",
)
def add_crm_contact(
    payload: NetworkingContactCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NetworkingContactResponse:
    contact = NetworkingCRMService.get_or_create_contact(
        db=db,
        user=current_user,
        data=payload,
    )
    rec_resp = (
        RecruiterProfileResponse.model_validate(contact.recruiter) if contact.recruiter else None
    )
    return NetworkingContactResponse(
        id=contact.id,
        user_id=contact.user_id,
        recruiter_id=contact.recruiter_id,
        company_id=contact.company_id,
        job_id=contact.job_id,
        application_id=contact.application_id,
        relationship_status=contact.relationship_status,
        contact_source=contact.contact_source,
        initial_contact_date=contact.initial_contact_date,
        last_contact_date=contact.last_contact_date,
        next_follow_up_date=contact.next_follow_up_date,
        communication_channel=contact.communication_channel,
        response_status=contact.response_status,
        response_received_at=contact.response_received_at,
        networking_notes=contact.networking_notes,
        tags=contact.tags or [],
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        recruiter=rec_resp,
        recent_activities=[
            NetworkingActivityResponse.model_validate(a) for a in (contact.activities or [])
        ],
    )


@router.patch(
    "/crm/contacts/{relationship_id}",
    response_model=NetworkingContactResponse,
    summary="Update relationship status, channel, notes, or follow-up date",
)
def update_crm_contact(
    relationship_id: uuid.UUID,
    payload: NetworkingContactUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NetworkingContactResponse:
    contact = NetworkingCRMService.update_contact(
        db=db,
        user=current_user,
        relationship_id=relationship_id,
        data=payload,
    )
    rec_resp = (
        RecruiterProfileResponse.model_validate(contact.recruiter) if contact.recruiter else None
    )
    return NetworkingContactResponse(
        id=contact.id,
        user_id=contact.user_id,
        recruiter_id=contact.recruiter_id,
        company_id=contact.company_id,
        job_id=contact.job_id,
        application_id=contact.application_id,
        relationship_status=contact.relationship_status,
        contact_source=contact.contact_source,
        initial_contact_date=contact.initial_contact_date,
        last_contact_date=contact.last_contact_date,
        next_follow_up_date=contact.next_follow_up_date,
        communication_channel=contact.communication_channel,
        response_status=contact.response_status,
        response_received_at=contact.response_received_at,
        networking_notes=contact.networking_notes,
        tags=contact.tags or [],
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        recruiter=rec_resp,
        recent_activities=[
            NetworkingActivityResponse.model_validate(a) for a in (contact.activities or [])
        ],
    )


@router.delete(
    "/crm/contacts/{relationship_id}",
    summary="Remove contact from Networking CRM",
)
def delete_crm_contact(
    relationship_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return NetworkingCRMService.delete_contact(
        db=db,
        user=current_user,
        relationship_id=relationship_id,
    )


# ---------------------------------------------------------------------------
# 3. AI Outreach Assistant
# ---------------------------------------------------------------------------


@router.post(
    "/outreach/generate",
    response_model=OutreachMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalized networking outreach message",
    description=(
        "Grounded in candidate's verified resume and career goals. Supports 7 message types."
    ),
)
def generate_outreach(
    payload: OutreachGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachMessageResponse:
    message = NetworkingCRMService.generate_outreach_message(
        db=db,
        user=current_user,
        data=payload,
    )
    return OutreachMessageResponse.model_validate(message)


@router.post(
    "/outreach/messages/{message_id}/approve",
    response_model=OutreachMessageResponse,
    summary="Approve outreach message draft",
    description="Explicit candidate review and approval gate before outreach dispatch.",
)
def approve_outreach(
    message_id: uuid.UUID,
    payload: OutreachApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutreachMessageResponse:
    message = NetworkingCRMService.approve_outreach_message(
        db=db,
        user=current_user,
        message_id=message_id,
        data=payload,
    )
    return OutreachMessageResponse.model_validate(message)


@router.post(
    "/outreach/messages/{message_id}/send-gmail",
    summary="Send approved outreach email via Gmail OAuth",
    description=(
        "Dispatches approved outreach email with optional resume attachment. "
        "Explicit confirmation (confirm_send=True) is strictly required."
    ),
)
def send_gmail_outreach(
    message_id: uuid.UUID,
    payload: OutreachSendGmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return NetworkingCRMService.send_outreach_via_gmail(
        db=db,
        user=current_user,
        message_id=message_id,
        confirm_send=payload.confirm_send,
        attach_resume=payload.attach_resume,
    )


# ---------------------------------------------------------------------------
# 4. Follow-up Intelligence
# ---------------------------------------------------------------------------


@router.get(
    "/follow-ups/due",
    response_model=FollowUpDueResponse,
    summary="Get actionable follow-ups due",
    description="Identifies recruiters with pending responses or scheduled follow-up dates.",
)
def get_due_followups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FollowUpDueResponse:
    return NetworkingCRMService.get_follow_up_recommendations(
        db=db,
        user=current_user,
    )
