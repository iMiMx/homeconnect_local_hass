"""Description for BSH.Common Entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity import EntityCategory
from homeconnect_websocket.entities import Execution

from .descriptions_definitions import (
    EntityDescriptions,
    HCButtonEntityDescription,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..appliance import HomeAppliance


def generate_start_button(appliance: "HomeAppliance") -> EntityDescriptions:
    """Describe the Start button.

    Previously this was only created if any programme had SELECT_AND_START.
    We now *always* create it when there are programmes at all, because
    START_ONLY programmes use a pending buffer and still need a Start button.
    """
    if len(appliance.programs) > 0:
        return HCButtonEntityDescription(
            key="button_start_program",
            entity="BSH.Common.Root.ActiveProgram",
            translation_key="start_program",
            category=EntityCategory.CONFIG,
        )
    return []
