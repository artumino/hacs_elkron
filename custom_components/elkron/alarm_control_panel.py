"""Interfaces with Elkron alarm control panels."""
import logging
import re

import voluptuous as vol

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_PASSWORD, CONF_USERNAME, STATE_ALARM_ARMED_AWAY, CONF_HOST, 
    STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED, STATE_ALARM_ARMED_CUSTOM_BYPASS)
import homeassistant.helpers.config_validation as cv

try:
    from homeassistant.components.alarm_control_panel import (
        AlarmControlPanelEntity as AlarmControlPanel,
    )
except ImportError:
    from homeassistant.components.alarm_control_panel import AlarmControlPanel

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Elkron'
CONF_STATES = 'states'
CONF_ZONES = 'zones'

STATE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ZONES, default=[]):
        vol.All(cv.ensure_list_csv, [cv.positive_int]),
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_STATES): vol.All(
            cv.ensure_list, [STATE_SCHEMA]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up a Elkron control panel."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    states = config.get(CONF_STATES)
    

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

class ElkronAlarm(AlarmControlPanel):
    """Representation of an Elkron status."""
    def __init__(self, hass, name, username, password, host, states):
        """Initialize the Elkron status."""
        from pylkron.elkron_client import ElkronClient
        _LOGGER.debug('Setting up ElkronClient...')
        self._hass = hass
        self._name = name
        self._username = username
        self._password = password
        self._hostname = host
        self._state = None

        #Setup States
        self._states = []
        for custom_state in states:
            if custom_state[CONF_NAME] != None and custom_state[CONF_ZONES] != None:
                new_state = ElkronState(custom_state[CONF_NAME], custom_state[CONF_ZONES])
                self._states.append(new_state)
                
                if custom_state[CONF_NAME] == STATE_ALARM_ARMED_HOME:
                    self._armed_home_state = new_state

                if custom_state[CONF_NAME] == STATE_ALARM_ARMED_AWAY:
                    self._armed_away_state = new_state

        self._alarm = ElkronClient(username, password, host)

    async def async_update(self):
        """Fetch the latest state."""
        await self._hass.async_add_executor_job(self._alarm.doLogin)
        sysState = await self._hass.async_add_executor_job(self._alarm.getDetailedStates)
        sysInfo = await self._hass.async_add_executor_job(self._alarm.getSysInfo)

        plantStructure = await self._hass.async_add_executor_job(self._alarm.getPlantStructure)
        zones = plantStructure['cfgzone']
        structure = []
        for zone in zones:
            structure.append({'name': zone['NAME'], 'zoneId': zone['NID']})
            
        self._state = { 'state': sysState, 'info': sysInfo, 'structure': structure }
        return self._state

    @property
    def name(self):
        """Return the name of the alarm."""
        return self._name

    @property
    def code_format(self):
        """Return one or more digits/characters."""
        return alarm.FORMAT_NUMBER

    @property
    def state(self):
        """Return the state of the device."""
        if self._state == None or 'state' not in self._state or self._state['state'] == None or 'activezone' not in self._state['state']:
            return None
        active_zones = self._state['state']['activezone']
        active_zones.sort()

        for custom_state in self._states:
            if custom_state.zones == active_zones:
                return custom_state.name
        
        if active_zones.__len__() == 0:
            return STATE_ALARM_DISARMED

        if active_zones.__len__() > 0:
            return STATE_ALARM_ARMED_CUSTOM_BYPASS

        return None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._state

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        if self._state == None or 'state' not in self._state or self._state['state'] == None or 'activezone' not in self._state['state']:
            _LOGGER.warning('Alarm not connected')
            return None

        try:
            await self._hass.async_add_executor_job(self._alarm.doDeactivate, code, self._state['state']['activezone'])
        except Exception as e:
            _LOGGER.warning('Failed to disarm alarm: ' + str(e))
            
        self.schedule_update_ha_state()

    async def async_alarm_arm_home(self, code=None):
        """Send arm hom command."""
        if self._state == None or 'state' not in self._state or self._state['state'] == None or 'activezone' not in self._state['state']:
            _LOGGER.warning('Alarm not connected')
            return None

        if self._armed_home_state == None:
            _LOGGER.error('No home state ( ' + STATE_ALARM_ARMED_HOME + ' ) declared for this alarm')

        try:
            await self._hass.async_add_executor_job(self._alarm.doActivate, code, self._armed_home_state.zones)
        except Exception as e:
            _LOGGER.warning('Failed to arm alarm: ' + str(e))

        self.schedule_update_ha_state()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if self._state == None or 'state' not in self._state or self._state['state'] == None or 'activezone' not in self._state['state']:
            _LOGGER.warning('Alarm not connected')
            return None
            
        if self._armed_away_state == None:
            _LOGGER.error('No away state ( ' + STATE_ALARM_ARMED_AWAY + ' ) declared for this alarm')

        try:
            await self._hass.async_add_executor_job(self._alarm.doActivate, code, self._armed_away_state.zones)
        except Exception as e:
            _LOGGER.warning('Failed to arm alarm: ' + str(e))

        self.schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        try:
            from homeassistant.components.alarm_control_panel import (
                SUPPORT_ALARM_ARM_AWAY,
                SUPPORT_ALARM_ARM_HOME
            )
        except ImportError:
            return 0
        return SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME