from functools import cached_property

import requests

from .utils import UNDEFINED, to_datetime, from_datetime, url
from .posts import WordPressPostsProxy
from .media import WordPressMediaProxy

class WordPressAPI:
    # cf https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/
    # TODO -- authentication auto catch success:
    #  - success_url
    # todo -- make this somehow a salt of the install environment?
    default_uuid = "80adaaed-dce3-48bc-aa36-a502483beac9"

    def __init__(self, host, username=None, app_password=UNDEFINED, *, app_name="WordPress Python API", app_uuid=None, debug=False, media_dir="./"):
        self.host = host
        self.session = requests.Session()
        self.session.headers.update({"Cache-Control": "no-cache"})
        self.app_name = app_name
        self.app_uuid = WordPressAPI.default_uuid if app_uuid is None else app_uuid
        self.username = username
        self.app_password = app_password
        if app_password is UNDEFINED:
            print("To authenticate this API, enter the app password from", self.authorization_url())
        else:
            self.session.auth = (username, app_password)
        self.debug = debug
        self.media_dir = media_dir

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
        if not (200 <= r.status_code < 300) and self.debug:
            print(r.text)
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
        if not (200 <= r.status_code < 300) and self.debug:
            print(r.text)
        r.raise_for_status()
        return r.json()
    
    @cached_property
    def info(self):
        return self.get("")

    @property
    def posts(self):
        return WordPressPostsProxy(self)
    
    @property
    def media(self):
        return WordPressMediaProxy(self, self.media_dir)

    @property
    def categories(self):
        result = {}
        for cat in self.paged("wp/v2/categories"):
            result[cat["id"]] = (cat["name"], cat["slug"], cat["description"])
        return result

    def category_ids(self, category_names, create_if_missing=False):
        required_categories = set(category_names)
        cat_ids = set()
        for (cat_id, (name, slug, desc)) in self.categories.items():
            name_lower = name.lower()
            matches = [cat_name for cat_name in required_categories if cat_name.lower() == name_lower]
            if matches:
                cat_ids.add(cat_id)
                for match in matches:
                    required_categories.remove(match)
        if required_categories:
            if not create_if_missing:
                raise ValueError(f"Categories not found: {required_categories!r}")
            for new_category_name in required_categories:
                new_cat = self.post("wp/v2/categories", json={"name": new_category})
                cat_ids.add(new_cat["id"])
        return cat_ids

    @property
    def tags(self):
        result = {}
        for tag in self.paged("wp/v2/tags"):
            result[tag["id"]] = (tag["name"], tag["slug"], tag["description"])
        return result

    def tag_ids(self, tag_names, create_if_missing=False):
        required_tags = set(tag_names)
        tag_ids = set()
        for (tag_id, (name, slug, desc)) in self.tags.items():
            name_lower = name.lower()
            matches = [tag_name for tag_name in required_tags if tag_name.lower() == name_lower]
            if matches:
                tag_ids.add(tag_id)
                for match in matches:
                    required_tags.remove(match)
        if required_tags:
            if not create_if_missing:
                raise ValueError(f"Tags not found: {required_tags!r}")
            for new_tag_name in required_tags:
                new_tag = self.post("wp/v2/tags", json={"name": new_tag_name})
                tag_ids.add(new_tag["id"])
        return tag_ids
