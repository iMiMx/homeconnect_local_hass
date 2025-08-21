"""Select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback
from homeconnect_websocket.entities import Execution

from .entity import HCEntity
from .helpers import create_entities

if TYPE_CHECKING:  # pragma: no cover
    from .appliance import HomeAppliance  # project-local helper
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: "HomeAssistant",
    entry: "ConfigEntry",
    async_add_entities: "AddEntitiesCallback",
) -> None:
    """Set up Home Connect Select entities."""
    create_entities(hass, entry, async_add_entities, HCProgramSelect)


class HCProgramSelect(HCEntity, SelectEntity):
    """Select entity for choosing a programme."""

    _attr_should_poll = False

    @property
    def options(self) -> list[str] | None:
        """Return list of available programmes (human readable names)."""
        if not self._appliance or not self._appliance.programs:
            return None
        # `_programs` is a dict like { "BSH.Common.Program....": Program }
        return list(self._appliance.rev_programs.keys())

    @property
    def current_option(self) -> str | None:
        """Return the currently active/selected programme (readable name)."""
        if not self._appliance:
            return None
        if self._appliance.selected_program is None:
            return None
        prog = self._appliance.selected_program
        # Map back to friendly name
        return self._appliance.programs.get(prog.name, prog.name) and self._appliance.rev_programs.get(
            prog.name, None
        )

    async def async_select_option(self, option: str) -> None:
        """
        Select a programme by its friendly name.

        Behaviour:
        - SELECT_ONLY           -> select() only
        - SELECT_AND_START      -> select() (or device’s own flow) and keep Start button available
        - START_ONLY (patched)  -> DO NOT auto-start; mark as pending and show Start button
        """
        if not self._appliance:
            return

        # Map the user-facing name back to the BSH id
        program_bsh = self._appliance.rev_programs[option]
        selected_program = self._appliance.programs[program_bsh]

        # Ensure we have a place to store a pending programme
        if not hasattr(self._appliance, "_pending_program"):
            # `_pending_program` holds a Program object that is selected but not yet started
            self._appliance._pending_program = None  # type: ignore[attr-defined]

        if selected_program.execution in (Execution.SELECT_ONLY, Execution.SELECT_AND_START):
            # Normal flow: just select (device may expose/require a later start)
            await selected_program.select()
            # Clear any previously pending start, since user made a fresh selection
            self._appliance._pending_program = None  # type: ignore[attr-defined]
        elif selected_program.execution == Execution.START_ONLY:
            # Two-step UX: buffer selection, don’t start yet
            # Some START_ONLY programmes don’t support select(); so we simply stash and refresh.
            self._appliance._pending_program = selected_program  # type: ignore[attr-defined]
            # Ask HA to refresh entities so Start button becomes available
            await self.coordinator.async_request_refresh()
        else:
            # Fallback – play it safe and do not auto-start
            self._appliance._pending_program = selected_program  # type: ignore[attr-defined]
            await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the appliance."""
        self.async_write_ha_state()
