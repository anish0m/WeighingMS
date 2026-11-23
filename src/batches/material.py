"""Material identity rules that need only the recipe snapshot (bolt 008, ADR-007).

Lot, container and tare come per component from OrgaTEX (Dummy OrgaTEX
training seed, OQ-7) and are already stored in ``SnapshotComponent``. This
module builds the component header and reports missing lot / container. It
holds no state; the identity check itself lives with the weighing session.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from batches.models import SnapshotComponent, Unit

MISSING = "—"
KG_PLACES = Decimal("0.001")


class MaterialFault(Enum):
    LOT_MISSING = "Lot missing for this component"
    CONTAINER_MISSING = "Container missing for this component"

    @property
    def code(self) -> str:
        return self.name


def format_quantity(amount: Decimal, unit: str) -> str:
    """Display text of a snapshot quantity, using Decimal only (NFR-16).

    Grams: no decimals when whole (``214 g``), otherwise without trailing
    zeros (``214.5 g``). Kilograms: three decimals (``1.850 kg``), more only
    if the value has them, so nothing is rounded away.
    """
    if unit == Unit.KILOGRAM:
        places = amount.quantize(KG_PLACES)
        text = f"{places:f}" if places == amount else f"{amount.normalize():f}"
    else:
        text = f"{amount.normalize():f}"
    return f"{text} {unit}"


@dataclass(frozen=True)
class ComponentHeader:
    name: str
    code: str
    lot: str
    container: str
    tare_text: str

    @property
    def text(self) -> str:
        """e.g. "Remazol Yellow RGB · DYE-4471 · LOT 2026-0387 · CONTAINER C-12 ·
        TARE 214 g"."""
        return (
            f"{self.name} · {self.code} · LOT {self.lot or MISSING}"
            f" · CONTAINER {self.container or MISSING} · TARE {self.tare_text}"
        )


def header_for(component: SnapshotComponent) -> ComponentHeader:
    return ComponentHeader(
        name=component.name,
        code=component.code,
        lot=component.lot.strip(),
        container=component.container.strip(),
        tare_text=format_quantity(component.tare, component.unit),
    )


def material_faults(component: SnapshotComponent) -> list[MaterialFault]:
    """Missing lot, then missing container (FR-5c, FR-6b). Blank counts as missing."""
    faults = []
    if not component.lot.strip():
        faults.append(MaterialFault.LOT_MISSING)
    if not component.container.strip():
        faults.append(MaterialFault.CONTAINER_MISSING)
    return faults
