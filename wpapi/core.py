from functools import cached_property

import requests

from .utils import UNDEFINED, to_datetime, from_datetime, url


class WordPressAPI:
    # cf https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/
    # TODO -- authentication auto catch success:
    #  - success_url
    # todo -- make this somehow a salt of the install environment?
    default_uuid = "80adaaed-dce3-48bc-aa36-a502483beac9"

    def __init__(self, host, username=None, app_password=UNDEFINED, *, app_name="WordPress Python API", app_uuid=None, debug=False):
        self.host = host
        self.session = requests.Session()
        self.app_name = app_name
        self.app_uuid = WordPressAPI.default_uuid if app_uuid is None else app_uuid
        self.username = username
        self.app_password = app_password
        if app_password is UNDEFINED:
            print("To authenticate this API, enter the app password from", self.authorization_url())
        else:
            self.session.auth = (username, app_password)
        self.debug = debug

    def authorization_url(self):
        info = self.info
        if "application-passwords" not in self.info.get("authentication", {}):
            raise RuntimeError("Application Passwords not available on this WordPress instance.")
        auth_url = info["authentication"]["application-passwords"]["endpoints"]["authorization"]
        return url(auth_url, app_name=self.app_name, app_id=self.app_uuid)

    def authenticate(self, username, password):
        self.username = username
        self.app_password = app_password
        self.session.auth = (username, app_password)

    def get(self, endpoint, **params):
        r = self.session.get(f"{self.host}/wp-json/{endpoint}", params=params)
        r.raise_for_status()
        return r.json()

    def paged(self, endpoint, per_page=10, **params):
        page = 1
        page_data = None
        while page_data is None or len(page_data) == per_page:
            page_data = self.get(endpoint, page=page, per_page=per_page, **params)
            yield from page_data
            page += 1

    def post(self, endpoint, **kwargs):
        r = self.session.post(f"{self.host}/wp-json/{endpoint}", **kwargs)
        r.raise_for_status()
        return r.json()
    
    @cached_property
    def info(self):
        return self.get()

    @property
    def posts(self):
        return WordPressPostsProxy(self)
    
    @property
    def categories(self):
        result = {}
        for cat in self.paged("wp/v2/categories"):
            result[cat["id"]] = (cat["name"], cat["slug"], cat["description"])
        return result
