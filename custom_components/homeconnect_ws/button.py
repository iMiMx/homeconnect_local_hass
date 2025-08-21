"""Button entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeconnect_websocket.entities import Execution

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: "HomeAssistant",
    entry: "ConfigEntry",
    async_add_entities: "AddEntitiesCallback",
) -> None:
    """Set up Home Connect Button entities."""
    create_entities(hass, entry, async_add_entities, HCStartButton)


class HCStartButton(HCEntity, ButtonEntity):
    """Start button for an active/pending programme."""

    _attr_should_poll = False

    @property
    def available(self) -> bool:
        """Available if:
        - device is available, and
        - there is a selected programme with SELECT_AND_START, or
        - a START_ONLY programme is pending selection (our patch)."""
        available = super().available
        if not available or not self._appliance:
            return False

        selected = self._appliance.selected_program
        pending = getattr(self._appliance, "_pending_program", None)

        if selected is not None and selected.execution == Execution.SELECT_AND_START:
            return True

        # Expose Start while a START_ONLY programme is pending
        if pending is not None:
            return True

        return False

    async def async_press(self) -> None:
        """Start the programme."""
        if not self._appliance:
            return

        # If we have a pending START_ONLY programme, start that and clear pending
        pending = getattr(self._appliance, "_pending_program", None)
        if pending is not None:
            await pending.start()
            self._appliance._pending_program = None  # type: ignore[attr-defined]
            await self.coordinator.async_request_refresh()
            return

        # Otherwise, start the currently selected programme (SELECT_AND_START path)
        if self._appliance.selected_program is not None:
            await self._appliance.selected_program.start()
