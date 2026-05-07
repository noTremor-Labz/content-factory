from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.database import get_db_session
from content_factory_api.modules.dependencies import get_current_user, require_roles
from content_factory_api.modules.domain import (
    MUTATION_ROLES,
    REVIEW_DECISION_ROLES,
    ComplianceCheckStatus,
    ComplianceRuleSeverity,
    ReviewTaskStatus,
)
from content_factory_api.modules.models import (
    ComplianceCheck,
    ComplianceRule,
    ContentItem,
    ReviewTask,
    User,
)
from content_factory_api.modules.schemas import (
    ComplianceCheckListResponse,
    ComplianceCheckRead,
    ComplianceRuleListResponse,
    ComplianceRuleRead,
)
from content_factory_api.modules.security import utcnow
from content_factory_api.modules.services import get_by_id_or_404, write_audit_log

router = APIRouter(prefix="/api/compliance", tags=["compliance"])

COMPLIANCE_RUN_ROLES = tuple(dict.fromkeys((*MUTATION_ROLES, *REVIEW_DECISION_ROLES)))


class ComplianceGateError(RuntimeError):
    """Raised when content lacks a final compliance decision for export/package."""


@dataclass(frozen=True)
class DefaultComplianceRule:
    key: str
    name: str
    description: str
    severity: ComplianceRuleSeverity
    reason_code: str
    terms: tuple[str, ...]
    risk_points: int
    message: str


DEFAULT_COMPLIANCE_RULES: tuple[DefaultComplianceRule, ...] = (
    DefaultComplianceRule(
        key="direct_purchase_cta",
        name="Direct purchase CTA",
        description="Blocks direct purchase, promo-code, discount, or ordering language.",
        severity=ComplianceRuleSeverity.HARD_FAIL,
        reason_code="direct_purchase_cta",
        terms=(
            "buy",
            "order now",
            "shop now",
            "promo code",
            "use code",
            "discount",
            "link in bio",
            "купи",
            "купить",
            "закажи",
            "заказать",
            "промокод",
            "скидка",
        ),
        risk_points=100,
        message="Direct purchase or promo CTA is not allowed for the pilot.",
    ),
    DefaultComplianceRule(
        key="health_or_reduced_risk_claim",
        name="Health or reduced-risk claim",
        description="Blocks safety, cessation, health, and reduced-risk claims.",
        severity=ComplianceRuleSeverity.HARD_FAIL,
        reason_code="health_or_reduced_risk_claim",
        terms=(
            "totally safe",
            "100% safe",
            "completely safe",
            "harmless",
            "healthy",
            "no risk",
            "risk free",
            "helps quit",
            "quit smoking",
            "better than cigarettes",
            "light",
            "mild",
            "low nicotine",
            "безопас",
            "без вреда",
            "помогает бросить",
            "легкий",
        ),
        risk_points=100,
        message="Health, cessation, or modified-risk claims require legal approval.",
    ),
    DefaultComplianceRule(
        key="youth_targeting",
        name="Youth targeting",
        description="Blocks teen, school, underage, and child-coded positioning.",
        severity=ComplianceRuleSeverity.HARD_FAIL,
        reason_code="youth_targeting",
        terms=(
            "teen",
            "teens",
            "kids",
            "school",
            "under 18",
            "minor",
            "подрост",
            "школь",
            "дети",
            "несовершеннолет",
        ),
        risk_points=100,
        message="Youth-coded or underage targeting cannot enter approval.",
    ),
    DefaultComplianceRule(
        key="product_use_demo",
        name="Product-use demonstration",
        description="Blocks explicit puffing, inhaling, vaping, or use instructions.",
        severity=ComplianceRuleSeverity.HARD_FAIL,
        reason_code="product_use_demo",
        terms=(
            "take a puff",
            "inhale",
            "vape it",
            "start vaping",
            "how to vape",
            "затяж",
            "вдохни",
            "парить",
            "вейпить",
        ),
        risk_points=100,
        message="Product-use demonstrations are outside the approved MVP lane.",
    ),
    DefaultComplianceRule(
        key="nicotine_or_vape_reference",
        name="Nicotine or vape reference",
        description="Flags nicotine, vape, e-cigarette, and smoking-alternative references.",
        severity=ComplianceRuleSeverity.SOFT_FLAG,
        reason_code="nicotine_or_vape_reference",
        terms=(
            "vape",
            "vaping",
            "e-cigarette",
            "ecigarette",
            "nicotine",
            "disposable",
            "smoking alternative",
            "вейп",
            "никотин",
            "электронная сигарета",
            "однораз",
            "inflave",
        ),
        risk_points=40,
        message="Nicotine or vape-adjacent placement requires reviewer attention.",
    ),
    DefaultComplianceRule(
        key="commercial_disclosure_missing",
        name="Commercial disclosure may be missing",
        description="Flags product placement when common sponsorship disclosure words are absent.",
        severity=ComplianceRuleSeverity.SOFT_FLAG,
        reason_code="commercial_disclosure_missing",
        terms=(
            "vape",
            "nicotine",
            "inflave",
            "вейп",
            "никотин",
        ),
        risk_points=25,
        message="Commercial nature may need disclosure or platform-specific handling.",
    ),
    DefaultComplianceRule(
        key="youth_appeal_flavor_or_style",
        name="Youth-appeal flavor or style",
        description="Flags fruit, candy, sweet, and flavor-led positioning.",
        severity=ComplianceRuleSeverity.SOFT_FLAG,
        reason_code="youth_appeal_flavor_or_style",
        terms=(
            "mango",
            "blueberry",
            "candy",
            "sweet",
            "fruit",
            "flavor",
            "манго",
            "черника",
            "конфета",
            "сладкий",
            "фрукт",
            "вкус",
        ),
        risk_points=35,
        message="Flavor or youth-appeal cues should be reviewed conservatively.",
    ),
)

DISCLOSURE_TERMS = (
    "#ad",
    "paid partnership",
    "sponsored",
    "advertisement",
    "реклама",
    "спонсор",
)


@router.get("/rules", response_model=ComplianceRuleListResponse)
def list_compliance_rules(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ComplianceRuleListResponse:
    ensure_default_compliance_rules(db_session)
    db_session.commit()
    rules = list(db_session.scalars(select(ComplianceRule).order_by(ComplianceRule.key.asc())))
    return ComplianceRuleListResponse(
        items=[ComplianceRuleRead.model_validate(rule) for rule in rules]
    )


@router.get("/checks", response_model=ComplianceCheckListResponse)
def list_compliance_checks(
    _current_user: Annotated[User, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ComplianceCheckListResponse:
    checks = list(
        db_session.scalars(select(ComplianceCheck).order_by(ComplianceCheck.created_at.desc()))
    )
    return ComplianceCheckListResponse(
        items=[ComplianceCheckRead.model_validate(check) for check in checks]
    )


@router.post(
    "/content-items/{content_item_id}/checks",
    response_model=ComplianceCheckRead,
    status_code=status.HTTP_201_CREATED,
)
def rerun_compliance_check(
    content_item_id: str,
    current_user: Annotated[User, Depends(require_roles(*COMPLIANCE_RUN_ROLES))],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ComplianceCheck:
    content_item = get_by_id_or_404(db_session, ContentItem, content_item_id, "Content item")
    check = run_compliance_check(
        db_session,
        content_item=content_item,
        actor_user_id=current_user.id,
    )
    db_session.commit()
    return check


def ensure_default_compliance_rules(db_session: Session) -> None:
    existing_rules = {
        rule.key: rule
        for rule in db_session.scalars(select(ComplianceRule)).all()
    }
    for default_rule in DEFAULT_COMPLIANCE_RULES:
        existing_rule = existing_rules.get(default_rule.key)
        pattern = "|".join(default_rule.terms)
        if existing_rule is None:
            db_session.add(
                ComplianceRule(
                    key=default_rule.key,
                    name=default_rule.name,
                    description=default_rule.description,
                    severity=default_rule.severity.value,
                    reason_code=default_rule.reason_code,
                    pattern=pattern,
                    enabled=True,
                )
            )
            continue

        existing_rule.name = default_rule.name
        existing_rule.description = default_rule.description
        existing_rule.severity = default_rule.severity.value
        existing_rule.reason_code = default_rule.reason_code
        existing_rule.pattern = pattern
    db_session.flush()


def run_compliance_check(
    db_session: Session,
    *,
    content_item: ContentItem,
    actor_user_id: str | None,
) -> ComplianceCheck:
    ensure_default_compliance_rules(db_session)
    rule_rows = list(
        db_session.scalars(
            select(ComplianceRule)
            .where(ComplianceRule.enabled.is_(True))
            .order_by(ComplianceRule.key.asc())
        )
    )
    default_by_key = {rule.key: rule for rule in DEFAULT_COMPLIANCE_RULES}
    normalized_text = _normalize_content_text(content_item)
    has_disclosure = any(term in normalized_text for term in DISCLOSURE_TERMS)
    flags: list[dict[str, object]] = []
    risk_score = 0

    for rule_row in rule_rows:
        default_rule = default_by_key.get(rule_row.key)
        if default_rule is None:
            continue
        if rule_row.key == "commercial_disclosure_missing" and has_disclosure:
            continue

        matched_terms = _matched_terms(default_rule.terms, normalized_text)
        if not matched_terms:
            continue

        flags.append(
            {
                "rule_key": default_rule.key,
                "severity": default_rule.severity.value,
                "reason_code": default_rule.reason_code,
                "message": default_rule.message,
                "matched_terms": matched_terms,
            }
        )
        if default_rule.severity == ComplianceRuleSeverity.HARD_FAIL:
            risk_score = max(risk_score, 100)
        if default_rule.severity == ComplianceRuleSeverity.SOFT_FLAG:
            risk_score += default_rule.risk_points

    hard_fail_count = sum(
        1 for flag in flags if flag["severity"] == ComplianceRuleSeverity.HARD_FAIL.value
    )
    if hard_fail_count > 0:
        status_value = ComplianceCheckStatus.FAILED.value
        risk_score = 100
    elif flags:
        status_value = ComplianceCheckStatus.FLAGGED.value
        risk_score = min(risk_score, 95)
    else:
        status_value = ComplianceCheckStatus.PASSED.value
        risk_score = 0

    check = ComplianceCheck(
        content_item_id=content_item.id,
        status=status_value,
        risk_score=risk_score,
        flags=flags,
        summary=_summary_for(
            status_value=status_value,
            flag_count=len(flags),
            hard_fail_count=hard_fail_count,
        ),
        evaluated_by_user_id=actor_user_id,
        evaluated_at=utcnow(),
    )
    db_session.add(check)
    db_session.flush()
    write_audit_log(
        db_session,
        actor_user_id=actor_user_id,
        action="compliance.check_completed",
        entity_type="compliance_check",
        entity_id=check.id,
        payload={
            "content_item_id": content_item.id,
            "status": check.status,
            "risk_score": check.risk_score,
            "flag_count": len(flags),
        },
    )
    return check


def latest_compliance_check(db_session: Session, content_item_id: str) -> ComplianceCheck | None:
    return db_session.scalar(
        select(ComplianceCheck)
        .where(ComplianceCheck.content_item_id == content_item_id)
        .order_by(ComplianceCheck.created_at.desc())
    )


def validate_compliance_for_review_approval(
    db_session: Session,
    *,
    content_item: ContentItem,
    compliance_override_reason: str | None,
) -> ComplianceCheck:
    check = latest_compliance_check(db_session, content_item.id)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Compliance check is required before review approval",
        )
    if check.status == ComplianceCheckStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Compliance check has hard failures and cannot be approved",
        )
    if check.status == ComplianceCheckStatus.FLAGGED.value and not _clean_reason(
        compliance_override_reason
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Compliance soft flags require an explicit override reason",
        )
    return check


def validate_final_compliance_decision(
    db_session: Session,
    *,
    content_item: ContentItem,
) -> ComplianceCheck:
    check = latest_compliance_check(db_session, content_item.id)
    if check is None:
        raise ComplianceGateError("Content item requires a compliance check before package export")
    if check.status == ComplianceCheckStatus.FAILED.value:
        raise ComplianceGateError("Content item has hard compliance failures")
    if check.status == ComplianceCheckStatus.PASSED.value:
        return check
    if check.status == ComplianceCheckStatus.FLAGGED.value and _has_soft_override(
        db_session,
        content_item_id=content_item.id,
        compliance_check_id=check.id,
    ):
        return check
    raise ComplianceGateError(
        "Compliance soft flags require reviewer override before package export"
    )


def ensure_final_compliance_decision_or_409(
    db_session: Session,
    *,
    content_item: ContentItem,
) -> ComplianceCheck:
    try:
        return validate_final_compliance_decision(db_session, content_item=content_item)
    except ComplianceGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _has_soft_override(
    db_session: Session,
    *,
    content_item_id: str,
    compliance_check_id: str,
) -> bool:
    tasks = db_session.scalars(
        select(ReviewTask).where(
            ReviewTask.content_item_id == content_item_id,
            ReviewTask.compliance_check_id == compliance_check_id,
            ReviewTask.status == ReviewTaskStatus.APPROVED.value,
        )
    )
    return any(_clean_reason(task.compliance_override_reason) is not None for task in tasks)


def _normalize_content_text(content_item: ContentItem) -> str:
    return f"{content_item.title}\n{content_item.script}".casefold()


def _matched_terms(terms: tuple[str, ...], normalized_text: str) -> list[str]:
    return [term for term in terms if _term_matches(term, normalized_text)]


def _term_matches(term: str, normalized_text: str) -> bool:
    if term.isascii() and any(character.isalnum() for character in term):
        pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
        return re.search(pattern, normalized_text) is not None
    return term in normalized_text


def _summary_for(*, status_value: str, flag_count: int, hard_fail_count: int) -> str:
    if status_value == ComplianceCheckStatus.PASSED.value:
        return "No compliance flags detected."
    if status_value == ComplianceCheckStatus.FAILED.value:
        return f"{hard_fail_count} hard compliance failure(s) detected."
    return f"{flag_count} soft compliance flag(s) require reviewer override."


def _clean_reason(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
