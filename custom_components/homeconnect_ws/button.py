"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Set

from homeassistant.components.button import ButtonEntity
from homeconnect_websocket.entities import Execution

from .entity import HCEntity
from .helpers import create_entities

# We import this so we can synthesize a description if the layer above omitted it
from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeconnect_websocket.entities import ActiveProgram, Command

    from . import HCConfigEntry
    from .entity_descriptions.descriptions_definitions import HCButtonEntityDescription

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    config_entry: HCConfigEntry,
    async_add_entites: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    entities: Set[HCEntity] = create_entities(
        {"button": HCButton, "start_button": HCStartButton},
        config_entry.runtime_data,
    )

    # --- Force-create Start button if the descriptions layer omitted it ---
    # If a Selected Program exists (program/select entities present), some models
    # can still start even when the execution flag isn't SELECT_AND_START.
    # On b10 the start_button may be filtered out; we add a minimal one here.
    has_start_button_already = any(isinstance(e, HCStartButton) for e in entities)

    aed = config_entry.runtime_data.available_entity_descriptions
    has_program_entities = ("program" in aed and aed["program"]) or ("select" in aed and aed["select"])

    if not has_start_button_already and has_program_entities:
        # Minimal description; HA will use this for the entity registry
        start_desc: HCButtonEntityDescription = HCButtonEntityDescription(
            key="start",
            name="Start",
            icon="mdi:play",
        )

        try:
            manual_start = HCStartButton(
                entity_description=start_desc,
                appliance=config_entry.runtime_data.appliance,
                device_info=config_entry.runtime_data.device_info,
            )
            entities.add(manual_start)
        except Exception:  # pragma: no cover — defensive
            # If anything goes wrong, we don't want setup to fail
            import logging

            logging.getLogger(__name__).exception("Failed to create manual Start button entity")

    async_add_entites(list(entities))


class HCButton(HCEntity, ButtonEntity):
    """Generic Button Entity (e.g., Abort)."""

    _entity: Command
    entity_description: HCButtonEntityDescription

    async def async_press(self) -> None:
        await self._entity.set_value(True)


class HCStartButton(HCEntity, ButtonEntity):
    """Start Button Entity."""

    _entity: ActiveProgram
    entity_description: HCButtonEntityDescription

    @property
    def available(self) -> bool:
        """
        Be permissive: if an appliance has a selected program, allow Start.

        Some appliances report execution != SELECT_AND_START (or None)
        even though starting is valid after selecting a program. The previous
        check hid the Start button in those cases.
        """
        if not super().available:
            return False
        return self._appliance.selected_program is not None

    async def async_press(self) -> None:
        # Start the currently selected program
        await self._appliance.selected_program.start()
