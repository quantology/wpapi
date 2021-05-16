import base64
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
from datetime import datetime
from pathlib import Path
import hashlib

import requests
from tqdm.auto import tqdm

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

def is_dir(path):
    if isinstance(path, str) and path.endswith("/"):
        return True
    return Path(path).is_dir()

def download_file(url, download_to=None, progress=False, exists_ok=True,
                  overwrite=False, ok_errs=None, chunk_size=8192, max_size=None):
    name = url.split("/")[-1]
    if download_to is None:
        download_to = name
    download_path = Path(download_to)
    if is_dir(download_to):
        download_path = download_path / name
    already_exists = download_path.exists()
    assert exists_ok or not already_exists, "File already exists"
    if already_exists and not overwrite:
        return download_path
    with requests.get(url, stream=True) as r:
        if ok_errs and r.status_code in ok_errs:
            return None
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        if max_size is not None and total_size > max_size:
            raise RuntimeError(f"File at {url!r} larger than max size: {total_size} > {max_size}")
        with tqdm(total=total_size, unit="iB", unit_scale=True,
            disable=not progress, desc=f"download {name}", leave=False) as pbar:
            try:
                with download_path.open(mode="wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:  # filter out keep-alive new chunks
                            pbar.update(len(chunk))
                            f.write(chunk)
            except:
                download_path.unlink()
                raise
    return download_path

def filehash(path, algo="sha1", buf_size=65536):
    h = hashlib.new(algo)
    with open(path, mode="rb") as fp:
        while True:
            data = fp.read(buf_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()
