from __future__ import annotations

from typing import Optional
from urllib.parse import unquote, urlparse

import requests


def validate_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Enter a valid http or https URL.")
    return cleaned


def probe_download(url: str, timeout: tuple[int, int] = (10, 20)) -> dict:
    with requests.Session() as session:
        response = session.head(url, allow_redirects=True, timeout=timeout)
        if response.status_code >= 400 or "Content-Length" not in response.headers:
            response = session.get(url, stream=True, allow_redirects=True, timeout=timeout)
        response.raise_for_status()

        headers = response.headers
        final_url = response.url
        total_bytes = int(headers.get("Content-Length", "0") or "0")
        accept_ranges = headers.get("Accept-Ranges", "").lower() == "bytes"

        if response.request.method == "GET":
            response.close()

    return {
        "final_url": final_url,
        "total_bytes": total_bytes,
        "supports_ranges": accept_ranges and total_bytes > 0,
        "filename": filename_from_headers(headers) or filename_from_url(final_url),
    }


def filename_from_headers(headers: requests.structures.CaseInsensitiveDict) -> Optional[str]:
    content_disposition = headers.get("Content-Disposition", "")
    if "filename=" not in content_disposition:
        return None

    filename_part = content_disposition.split("filename=", 1)[1].strip()
    if filename_part.startswith(("'", '"')) and filename_part.endswith(("'", '"')):
        filename_part = filename_part[1:-1]
    return unquote(filename_part)


def filename_from_url(url: str) -> str:
    path = urlparse(url).path.rsplit("/", 1)[-1]
    filename = unquote(path).strip()
    return filename or "download.bin"
