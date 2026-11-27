"""Storage backend dispatch (app/storage.py): local disk by default, Vercel
Blob when BLOB_READ_WRITE_TOKEN is set — see config.py's `use_blob_storage`.
The Blob branch is exercised against a fake `vercel.blob.sync` module (no
real network/credentials needed) so this runs in CI the same as everything
else.
"""
from __future__ import annotations

import io
import sys
import types

import pytest
from PIL import Image

from app import storage


@pytest.fixture
def local_storage(monkeypatch, tmp_path):
    # get_settings() re-reads the environment on every call (no caching —
    # see config.py), so these just need to be set before storage.py calls it.
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    return tmp_path


def test_local_save_read_delete_roundtrip(local_storage):
    handle = storage.save_upload_bytes(1, "xray.png", b"fake-bytes")
    assert storage.read_case_image_bytes(handle) == b"fake-bytes"

    storage.delete_case_image(handle)
    assert storage.read_case_image_bytes(handle) is None


def test_local_read_missing_handle_returns_none(local_storage):
    assert storage.read_case_image_bytes(None) is None
    assert storage.read_case_image_bytes(str(local_storage / "nope.png")) is None


def test_local_save_heatmap_and_display_images(local_storage):
    image = Image.new("RGB", (4, 4), (10, 20, 30))

    heatmap_handle = storage.save_heatmap_image(2, image)
    display_handle = storage.save_display_image(2, image)
    layer_handle = storage.save_heatmap_layer_image(2, image.convert("RGBA"))

    for handle in (heatmap_handle, display_handle, layer_handle):
        data = storage.read_case_image_bytes(handle)
        assert data is not None
        assert Image.open(io.BytesIO(data)).size == (4, 4)


def test_delete_case_image_is_a_noop_for_none(local_storage):
    storage.delete_case_image(None)  # must not raise


class _FakeBlobModule(types.SimpleNamespace):
    """Stands in for `vercel.blob.sync` — records calls, serves bytes out of
    an in-memory dict keyed by pathname, same contract as the real SDK
    (see storage.py's `_blob_*` functions)."""

    def __init__(self):
        super().__init__()
        self.store: dict[str, bytes] = {}
        self.deleted: list[str] = []

        class _Result:
            def __init__(self, pathname):
                self.pathname = pathname

        class _GetResult:
            def __init__(self, body):
                self.body = body

        class BlobNotFoundError(Exception):
            pass

        self.BlobNotFoundError = BlobNotFoundError

        def put_blob(pathname, data, access, content_type=None, allow_overwrite=False):
            self.store[pathname] = data
            return _Result(pathname)

        def get_blob(pathname, access):
            if pathname not in self.store:
                raise BlobNotFoundError(pathname)
            return _GetResult(self.store[pathname])

        def delete_blob(pathname):
            self.deleted.append(pathname)
            self.store.pop(pathname, None)

        self.put_blob = put_blob
        self.get_blob = get_blob
        self.delete_blob = delete_blob


@pytest.fixture
def blob_storage(monkeypatch):
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "fake-token-for-tests")

    fake_blob = _FakeBlobModule()
    fake_vercel_blob_pkg = types.ModuleType("vercel.blob")
    fake_vercel_blob_pkg.sync = fake_blob
    fake_vercel_pkg = types.ModuleType("vercel")
    fake_vercel_pkg.blob = fake_vercel_blob_pkg

    monkeypatch.setitem(sys.modules, "vercel", fake_vercel_pkg)
    monkeypatch.setitem(sys.modules, "vercel.blob", fake_vercel_blob_pkg)
    return fake_blob


def test_blob_backend_selected_when_token_set(blob_storage):
    from app.config import get_settings

    assert get_settings().use_blob_storage is True


def test_blob_save_read_delete_roundtrip(blob_storage):
    handle = storage.save_upload_bytes(3, "xray.png", b"blob-bytes")
    assert handle.startswith("cases/3/")
    assert blob_storage.store[handle] == b"blob-bytes"

    assert storage.read_case_image_bytes(handle) == b"blob-bytes"

    storage.delete_case_image(handle)
    assert handle in blob_storage.deleted
    assert storage.read_case_image_bytes(handle) is None


def test_blob_read_missing_handle_returns_none(blob_storage):
    assert storage.read_case_image_bytes("cases/99/does-not-exist.png") is None
