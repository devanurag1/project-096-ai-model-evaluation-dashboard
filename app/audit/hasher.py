"""Cryptographic hashing utilities for canonical JSON and files."""
import hashlib
import json
from pathlib import Path
from typing import Any, Union


def canonical_json_dumps(obj: Any) -> str:
    """Serialize object to deterministic, sorted-key JSON string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def compute_sha256(data: Union[str, bytes, dict, list]) -> str:
    """Compute SHA-256 hex digest of data."""
    if isinstance(data, (dict, list)):
        raw = canonical_json_dumps(data).encode("utf-8")
    elif isinstance(data, str):
        raw = data.encode("utf-8")
    elif isinstance(data, bytes):
        raw = data
    else:
        raw = str(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    if not file_path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
