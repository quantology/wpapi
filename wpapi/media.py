from pathlib import Path
from typing import Optional, Iterable
from tempfile import TemporaryDirectory
from datetime import datetime
from uuid import uuid4

import mistune

from .utils import from_datetime, to_datetime, download_file, is_dir, filehash

class WordPressMedia:
    # https://developer.wordpress.org/rest-api/reference/posts/
    @classmethod
    def from_file(cls, path, metadata, *, wp_api=None):
        copied_metadata = dict(metadata)
        # TODO -- replace create / modified with path modified time if DNE
        if "date" not in copied_metadata:
            copied_metadata["date"] = from_datetime(datetime.utcfromtimestamp(Path(path).stat().st_mtime))
        copied_metadata["date"] = from_datetime(copied_metadata["date"])
        copied_metadata["modified"] = from_datetime(copied_metadata.get("modified", copied_metadata["date"]))
        return cls(path, copied_metadata, wp_api=wp_api)

    def __init__(self, path, metadata, *, wp_api=None):
        if path is None or is_dir(path):
            filename = metadata["media_details"].get("file", "").split("/")[-1]
            if path is None:
                path = Path(f"./{filename}")
            else:
                path = Path(path) / filename
        elif isinstance(path, str):
            path = Path(path)
        self.path = path
        self.metadata = metadata
        self.wp_api = wp_api

    def copy(self, path=None, wp_api=None, **with_metadata):
        new_metadata = self.metadata.copy()
        new_metadata.update(with_metadata)
        wp_api = self.wp_api if wp_api is None else wp_api
        path = self.path if path is None else path
        return WordPressMedia(path, new_metadata, wp_api=wp_api)

    @property
    def url(self):
        return self.metadata["source_url"]

    def download(self, to_path=None, replace_existing=False, **kwargs):
        path = self.path if to_path is None else Path(to_path)
        if path.exists() and not replace_existing:
            raise RuntimeError(f"File already exists at {path!r}: use replace_existing=True to overwrite.")
        return download_file(self.url, path, **kwargs)
    
    def local_hash(self, algo="sha1"):
        return filehash(self.path, algo=algo)
    
    @property
    def local_mtime(self):
        return self.path.stat().st_mtime

    def remote_hash(self, algo="sha1", **kwargs):
        with TemporaryDirectory() as tmpdir:
            path = self.download(to_path=tmpdir, replace_existing=True, **kwargs)
            return filehash(path, algo=algo)
    
    @property
    def remote_mtime(self):
        return to_datetime(self.metadata["modified_gmt"]).timestamp()

    def __repr__(self):
        # ..?
        return f"<Media ...>"

    def in_sync(self, hash_algo="sha1"):
        return self.local_hash(algo=hash_algo) == self.remote_hash(algo=hash_algo)

    def sync(self, check_sync=True):
        # picks whichever has been updated more recently; either upload or download based on timestamp
        if self.path.exists() and check_sync and self.in_sync():
            return
        if self.path.exists() and self.local_mtime > self.remote_mtime:
            self.upload()
        else:
            self.download(replace_existing=True)

    def upload(self):
        assert self.wp_api is not None
        assert self.path.exists()
        existing_id = self.metadata.get("id")
        if existing_id is None:
            existing_post = self.wp_api.media.get(self.metadata["slug"])
            if existing_post is not None:
                existing_id = existing_post.metadata["id"]
            elif self.wp_api.debug:
                print("none existing:", self.metadata["slug"])
        post_to_url = "wp/v2/media/"
        if existing_id is not None:
            if self.wp_api.debug:
                print("updating existing:", existing_id)
            post_to_url += str(existing_id)
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".webp": "image/webp"
        }[self.path.suffix.lower()]
        # doesn't work
        #result = self.wp_api.post(post_to_url, files={
        #    'upload_file': (self.path.name, self.path.open(mode="rb"), mime_type, {'Content-Disposition':'form-data'})})
        # from https://stackoverflow.com/a/44961468:
        if "slug" in self.metadata:
            fname = f"{self.metadata['slug']}{self.path.suffix}"
        else:
            fname = self.path.name
        result = self.wp_api.post(post_to_url,
                                 data=self.path.open(mode="rb").read(),
                                 headers={"Content-Type": "",
                                          "Content-Disposition": f"attachment; filename={fname}"})

        #assert result["slug"] == self.metadata["slug"], f"Returned: {result!r}"
        return result

class WordPressMediaProxy:
    # todo -- filtering, select by tags, setting, etc.
    def __init__(self, wp_api, local_dir=None):
        self.wp_api = wp_api
        self.local_dir = local_dir

    def __iter__(self) -> Iterable[WordPressMedia]:
        for media_data in self.wp_api.paged("wp/v2/media/"):
            yield WordPressMedia(self.local_dir, media_data, wp_api=self.wp_api)

    def get(self, key, local_dir=None) -> Optional[WordPressMedia]:
        if isinstance(key, str):
            slug = key
            media = list(self.wp_api.paged("wp/v2/media", slug=slug, nocache=str(uuid4())))
            if not media:
                return None
            if self.wp_api.debug and len(media) > 1:
                print(media)
            assert len(media) == 1
            if local_dir is None:
                local_dir = self.local_dir
            media_data = media[0]
        elif isinstance(key, int):
            id_ = key
            media_data = self.wp_api.get(f"wp/v2/media/{id_}")
        return WordPressMedia(local_dir, media_data, wp_api=self.wp_api)

    def __getitem__(self, key) -> WordPressMedia:
        if isinstance(key, (str, int)):
            result = self.get(key)
            if result is None:
                if isinstance(key, str):
                    raise KeyError(f"Media with slug {key} not found on WordPress at {self.wp_api.host}")
                if isinstance(key, int):
                    raise KeyError(f"Media with id {key} not found on WordPress at {self.wp_api.host}")
            return result

    def __setitem__(self, slug, media: WordPressMedia):
        slugged_media = media.copy(slug=slug, wp_api=self.wp_api)
        slugged_media.upload()
