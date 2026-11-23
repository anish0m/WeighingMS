"""Dyestuff identity verification and material readiness (bolt 008).

The browser names a scan by its ``scanId``; the server re-reads the scanner's
latest scan through its adapter and compares the *scanner's* code with the
snapshot component's code (ADR-006). Checks are members of the weighing
session (ADR-007). ``check_material_ready`` is the material gate that the
confirmation (bolt 010) must pass first.
"""

import logging
from dataclasses import dataclass
from enum import Enum

from django.db import IntegrityError, transaction

from batches.material import ComponentHeader, header_for, material_faults
from batches.models import SnapshotComponent
from devices import scanner
from weighing.models import IdentityCheck, IdentityResult, Operator, WeighingSession
from weighing.services import RefusalReason, WeighingRefused, require_operator

logger = logging.getLogger(__name__)

RESULT_MESSAGE = {
    IdentityResult.VERIFIED: "Dyestuff verified",
    IdentityResult.WRONG_DYESTUFF: RefusalReason.WRONG_DYESTUFF.value,
}


class IdentityStatus(Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    WRONG_DYESTUFF = "wrong_dyestuff"


@dataclass(frozen=True)
class ComponentView:
    """One snapshot component with its header, identity and readiness."""

    component: SnapshotComponent
    header: ComponentHeader
    status: IdentityStatus
    latest_check: IdentityCheck | None
    refusal: RefusalReason | None


def _refuse(reason: RefusalReason, session_id, sequence) -> WeighingRefused:
    logger.info(
        "IdentityCheckRefused session=%s sequence=%s reason=%s",
        session_id,
        sequence,
        reason.code,
    )
    return WeighingRefused(reason)


def load_session(session_id: int) -> WeighingSession:
    session = (
        WeighingSession.objects.select_related("selection")
        .filter(pk=session_id)
        .first()
    )
    if session is None:
        raise WeighingRefused(RefusalReason.SESSION_NOT_FOUND)
    return session


def load_component(session: WeighingSession, sequence: int) -> SnapshotComponent:
    component = session.selection.components.filter(sequence=sequence).first()
    if component is None:
        raise _refuse(RefusalReason.COMPONENT_NOT_FOUND, session.pk, sequence)
    return component


def verify_identity(
    session_id: int, sequence: int, scan_id: int, operator_id: str | None
) -> tuple[IdentityCheck, bool]:
    """Check scan ``scan_id`` against component ``sequence``; ``(check, created)``.

    A scan already recorded for the session is returned unchanged. Every
    refusal raises ``WeighingRefused`` and stores nothing.
    """
    operator = require_operator(operator_id, "verify_identity")
    session = load_session(session_id)
    component = load_component(session, sequence)
    existing = session.identity_checks.filter(scan_id=scan_id).first()
    if existing is not None:
        return existing, False
    try:
        scan = scanner.read_latest_scan()
    except scanner.ScannerUnavailable as exc:
        raise _refuse(RefusalReason.SCANNER_UNAVAILABLE, session.pk, sequence) from exc
    if scan is None or scan.scan_id != scan_id:
        raise _refuse(RefusalReason.SCAN_NOT_CURRENT, session.pk, sequence)
    if scan.kind != "dyestuff":
        raise _refuse(RefusalReason.NOT_A_DYESTUFF_SCAN, session.pk, sequence)
    expected = component.code.strip()
    scanned = scan.code.strip()
    result = (
        IdentityResult.VERIFIED
        if scanned == expected
        else IdentityResult.WRONG_DYESTUFF
    )
    try:
        with transaction.atomic():
            check = IdentityCheck.objects.create(
                session=session,
                component_sequence=component.sequence,
                expected_code=expected,
                scan_id=scan.scan_id,
                scanned_code=scanned,
                result=result,
                operator=Operator.objects.get(operator_id=operator.operator_id),
            )
    except IntegrityError:
        # The same scan was recorded concurrently: return that check.
        return session.identity_checks.get(scan_id=scan_id), False
    _log_check(check, session)
    return check, True


def _log_check(check: IdentityCheck, session: WeighingSession) -> None:
    if check.result == IdentityResult.VERIFIED:
        logger.info(
            "DyestuffVerified session=%s batch=%s sequence=%s code=%s scan=%s"
            " operator=%s",
            session.pk,
            session.batch_id,
            check.component_sequence,
            check.scanned_code,
            check.scan_id,
            check.operator.operator_id,
        )
    else:
        logger.warning(
            "WrongDyestuffScanned session=%s batch=%s sequence=%s expected=%s"
            " scanned=%s scan=%s operator=%s",
            session.pk,
            session.batch_id,
            check.component_sequence,
            check.expected_code,
            check.scanned_code,
            check.scan_id,
            check.operator.operator_id,
        )


def identity_status(
    session: WeighingSession, sequence: int
) -> tuple[IdentityStatus, IdentityCheck | None]:
    """The latest check of the component decides (a later wrong scan blocks again)."""
    latest = (
        session.identity_checks.filter(component_sequence=sequence)
        .order_by("-checked_at", "-pk")
        .first()
    )
    if latest is None:
        return IdentityStatus.UNVERIFIED, None
    return IdentityStatus(latest.result), latest


def _readiness(
    component: SnapshotComponent, status: IdentityStatus
) -> RefusalReason | None:
    faults = material_faults(component)
    if faults:
        return RefusalReason[faults[0].code]
    if status is IdentityStatus.UNVERIFIED:
        return RefusalReason.IDENTITY_NOT_VERIFIED
    if status is IdentityStatus.WRONG_DYESTUFF:
        return RefusalReason.WRONG_DYESTUFF
    return None


def check_material_ready(session: WeighingSession, sequence: int) -> None:
    """Material gate for confirming a component (FR-4d, FR-5c, FR-6b).

    Refuses, in this order: LOT_MISSING, CONTAINER_MISSING,
    IDENTITY_NOT_VERIFIED, WRONG_DYESTUFF. Bolt 010's confirm calls it first.
    """
    component = load_component(session, sequence)
    status, _ = identity_status(session, sequence)
    reason = _readiness(component, status)
    if reason is not None:
        raise _refuse(reason, session.pk, sequence)


def session_components(session_id: int) -> tuple[WeighingSession, list[ComponentView]]:
    """Every snapshot component in sequence with header, identity and readiness."""
    session = load_session(session_id)
    views = []
    for component in session.selection.components.all():
        status, latest = identity_status(session, component.sequence)
        views.append(
            ComponentView(
                component=component,
                header=header_for(component),
                status=status,
                latest_check=latest,
                refusal=_readiness(component, status),
            )
        )
    return session, views
