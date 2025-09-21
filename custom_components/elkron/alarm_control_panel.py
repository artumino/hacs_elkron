"""Interfaces with Elkron alarm control panels."""

import logging
import re

from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, CONF_HOST
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelState,
    CodeFormat,
)
from pylkron.elkron_client import ElkronClient
from .const import (
    DOMAIN,
    CONF_AWAY_ZONES,
    CONF_HOME_ZONES,
    CONF_STATES,
    DEFAULT_NAME,
    CONF_ZONES,
)

_LOGGER = logging.getLogger(__name__)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from typing import Any, Mapping
from propcache.api import cached_property
import homeassistant.helpers.config_validation as cv


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Elkron control panel."""
    config = config_entry.data
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    away_zones = [int(x) for x in cv.ensure_list_csv(config.get(CONF_AWAY_ZONES, ""))]
    home_zones = [int(x) for x in cv.ensure_list_csv(config.get(CONF_HOME_ZONES, ""))]
    states = [
        {"name": CONF_AWAY_ZONES, "zones": away_zones},
        {"name": CONF_HOME_ZONES, "zones": home_zones},
    ]

    elkronalarm = ElkronAlarm(hass, name, username, password, host, states)
    async_add_entities([elkronalarm])


class ElkronState:
    def __init__(self, name, zones):
        self._name = name
        self._zones = zones
        self._zones.sort()

    @property
    def name(self):
        return self._name

    @property
    def zones(self):
        return self._zones


class ElkronAlarm(AlarmControlPanelEntity):
    """Representation of an Elkron status."""

    def __init__(self, hass, name, username, password, host, states):
        """Initialize the Elkron status."""
        _LOGGER.debug("Setting up ElkronClient...")
        self._hass = hass
        self._name = name
        self._username = username
        self._password = password
        self._hostname = host
        self._state = None

        # Setup States
        self._states = []
        for custom_state in states:
            if custom_state[CONF_NAME] != None and custom_state[CONF_ZONES] != None:
                new_state = ElkronState(
                    custom_state[CONF_NAME], custom_state[CONF_ZONES]
                )
                self._states.append(new_state)

                if custom_state[CONF_NAME] == AlarmControlPanelState.ARMED_HOME:
                    self._armed_home_state = new_state

                if custom_state[CONF_NAME] == AlarmControlPanelState.ARMED_AWAY:
                    self._armed_away_state = new_state

        self._alarm: ElkronClient = ElkronClient(username, password, host)

    async def async_update(self):
        """Fetch the latest state."""
        await self._hass.async_add_executor_job(self._alarm.doLogin)
        sysState = await self._hass.async_add_executor_job(
            self._alarm.getDetailedStates
        )
        sysInfo = await self._hass.async_add_executor_job(self._alarm.getSysInfo)

        plantStructure = await self._hass.async_add_executor_job(
            self._alarm.getPlantStructure
        )
        zones = plantStructure["cfgzone"]
        structure = []
        for zone in zones:
            structure.append({"name": zone["NAME"], "zoneId": zone["NID"]})

        self._state = {"state": sysState, "info": sysInfo, "structure": structure}
        return self._state

    @property
    def name(self):
        """Return the name of the alarm."""
        return self._name

    @property
    def code_format(self) -> CodeFormat | None:
        """Return one or more digits/characters."""
        return CodeFormat.NUMBER

    def _calculate_alarm_state(self) -> AlarmControlPanelState | None:
        """Calculate the alarm state."""
        if (
            self._state == None
            or "state" not in self._state
            or self._state["state"] == None
            or "activezone" not in self._state["state"]
        ):
            return None
        active_zones = self._state["state"]["activezone"]
        active_zones.sort()

        if active_zones.__len__() == 0:
            return AlarmControlPanelState.DISARMED

        if active_zones.__len__() > 0:
            return AlarmControlPanelState.ARMED_CUSTOM_BYPASS

        return None

    @cached_property
    def alarm_state(self) -> AlarmControlPanelState | None:
        calculated_state = self._calculate_alarm_state()
        if calculated_state is None:
            return None

        for custom_state in self._states:
            if custom_state.zones == active_zones:
                return custom_state.name

        return calculated_state

    @cached_property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes."""
        return self._state

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        if (
            self._state == None
            or "state" not in self._state
            or self._state["state"] == None
            or "activezone" not in self._state["state"]
        ):
            _LOGGER.warning("Alarm not connected")
            return None

        try:
            await self._hass.async_add_executor_job(
                self._alarm.doDeactivate, code, self._state["state"]["activezone"]
            )
        except Exception as e:
            _LOGGER.warning("Failed to disarm alarm: " + str(e))

        self.schedule_update_ha_state()

    async def async_alarm_arm_home(self, code=None):
        """Send arm hom command."""
        if (
            self._state == None
            or "state" not in self._state
            or self._state["state"] == None
            or "activezone" not in self._state["state"]
        ):
            _LOGGER.warning("Alarm not connected")
            return None

        if self._armed_home_state == None:
            _LOGGER.error(
                "No home state ( "
                + AlarmControlPanelState.ARMED_HOME
                + " ) declared for this alarm"
            )

        try:
            await self._hass.async_add_executor_job(
                self._alarm.doActivate, code, self._armed_home_state.zones
            )
        except Exception as e:
            _LOGGER.warning("Failed to arm alarm: " + str(e))

        self.schedule_update_ha_state()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if (
            self._state == None
            or "state" not in self._state
            or self._state["state"] == None
            or "activezone" not in self._state["state"]
        ):
            _LOGGER.warning("Alarm not connected")
            return None

        if self._armed_away_state == None:
            _LOGGER.error(
                "No away state ( "
                + AlarmControlPanelState.ARMED_AWAY
                + " ) declared for this alarm"
            )

        try:
            await self._hass.async_add_executor_job(
                self._alarm.doActivate, code, self._armed_away_state.zones
            )
        except Exception as e:
            _LOGGER.warning("Failed to arm alarm: " + str(e))

        self.schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        try:
            from homeassistant.components.alarm_control_panel import (
                SUPPORT_ALARM_ARM_AWAY,
                SUPPORT_ALARM_ARM_HOME,
            )
        except ImportError:
            return 0
        return SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME
