import base64
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from datetime import datetime

__all__ = ["UNDEFINED", "WP_DATETIME_FMT", "to_datetime", "from_datetime", "url"]

UNDEFINED = object()
WP_DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"

def to_datetime(dt):
    if isinstance(dt, str):
        return datetime.strptime(dt, WP_DATETIME_FMT)
    return dt

def from_datetime(dt):
    if not isinstance(dt, str):
        return dt.strftime(WP_DATETIME_FMT)
    return dt

def url(base_url,  **params):
    parsed = urlparse(base_url)
    existing_params = dict(parse_qsl(parsed.query))
    existing_params.update(params)
    new_parsed = parsed._replace(query=urlencode(existing_params))
    return urlunparse(new_parsed)
