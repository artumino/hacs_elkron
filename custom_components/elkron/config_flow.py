from homeassistant import config_entries
from homeassistant.components.alarm_control_panel import PLATFORM_SCHEMA

import voluptuous as vol

from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, CONF_HOST
from .const import DOMAIN, CONF_STATES, CONF_ZONES, DEFAULT_NAME
import homeassistant.helpers.config_validation as cv



STATE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ZONES, default=[]):
        vol.All(cv.ensure_list_csv, [cv.positive_int]),
})

PLATFORM_SCHEMA: cv.PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_STATES): vol.All(
            cv.ensure_list, [STATE_SCHEMA]),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

class ElkronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Elkron config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, info):
        if info is not None:
            pass  # TODO: process info

        return self.async_show_form(
            step_id="user", data_schema=PLATFORM_SCHEMA
        )