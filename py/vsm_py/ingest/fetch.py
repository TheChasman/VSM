"""Download and checksum verification. A file on disk is never overwritten."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import httpx

from . import IngestError
from .sources import Source

USER_AGENT = "vsm-ingest (+https://github.com/TheChasman/VSM)"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure(source: Source, data_dir: Path, client: httpx.Client | None = None) -> Path:
    """Return the verified local file for `source`, downloading it if absent.

    An existing file is the archived copy: it is verified and used, never replaced.
    A mismatch stops with both hashes. A source with no pinned hash stops and reports
    the hash to pin, so nothing unverified reaches reference.sqlite.
    """
    dest = source.path(data_dir)
    if dest.exists():
        _verify(source, sha256_file(dest), dest)
        return dest
    if source.fetch == "manual":
        raise IngestError(f"{source.id}: place the file at {dest} by hand ({source.url})")

    dest.parent.mkdir(parents=True, exist_ok=True)
    own_client = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    try:
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                with client.stream("GET", source.url) as r:
                    r.raise_for_status()
                    if r.status_code != 200:
                        # e.g. 202 "file is being generated": never hash a placeholder.
                        raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                    for chunk in r.iter_bytes():
                        tmp.write(chunk)
            except httpx.HTTPError as e:
                tmp_path.unlink(missing_ok=True)
                raise IngestError(f"{source.id}: download failed and no archived copy: {e}") from e
        try:
            _verify(source, sha256_file(tmp_path), dest)
        except IngestError:
            tmp_path.unlink(missing_ok=True)
            raise
        tmp_path.rename(dest)
        return dest
    finally:
        if own_client:
            client.close()


def _verify(source: Source, actual: str, where: Path) -> None:
    if not source.sha256:
        raise IngestError(
            f"{source.id}: no sha256 pinned in sources.toml. Downloaded file hashes to {actual}"
        )
    if actual != source.sha256:
        raise IngestError(
            f"{source.id}: checksum mismatch for {where}: expected {source.sha256}, got {actual}. "
            "Nothing was overwritten."
        )
