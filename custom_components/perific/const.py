from __future__ import annotations

from datetime import timedelta
from logging import getLogger

DOMAIN = "perific"
LOGGER = getLogger(__package__)

DEFAULT_API_URL = "https://api.enegic.com"
SCAN_INTERVAL = timedelta(seconds=30)

CONF_ITEM_ID = "item_id"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_TOKEN_VALID_TO = "token_valid_to"
CONF_USERNAME = "username"
CONF_USER_ID = "user_id"

SENSOR_GRID_POWER_KEY = "grid_power"
SENSOR_GRID_POWER_STATUS_KEY = "grid_power_status"
