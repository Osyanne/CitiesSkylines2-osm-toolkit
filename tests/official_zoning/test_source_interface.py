"""Test the Source protocol — interface compliance for any city source module."""
import inspect
from pathlib import Path
from official_zoning.source_interface import Source


def test_source_protocol_has_required_methods():
    members = {name for name, _ in inspect.getmembers(Source) if not name.startswith("_")}
    assert "download" in members
    assert "read" in members
    # Check that slug is in __annotations__ for Protocol
    assert hasattr(Source, "__annotations__")
    assert "slug" in Source.__annotations__


def test_source_download_signature():
    sig = inspect.signature(Source.download)
    params = list(sig.parameters)
    assert "cache_dir" in params, f"download() missing cache_dir param: {params}"


def test_source_read_signature():
    sig = inspect.signature(Source.read)
    params = list(sig.parameters)
    assert "cache_path" in params, f"read() missing cache_path param: {params}"
