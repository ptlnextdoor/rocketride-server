# =============================================================================
# MIT License
# Copyright (c) 2026 Aparavi Software AG
# =============================================================================

"""store_chroma render (#3353).

render asked Chroma for the documents only and then read each chunk's id from
the metadatas. Chroma returns None for a field that a request leaves out, so
rendering any stored document raised TypeError.
"""

from __future__ import annotations

from .test_convert_filter_explicit_none import _load_store_class
from .test_mark_deleted import _FakeCollection, _rows


def test_render_returns_every_chunk_in_order():
    store_cls = _load_store_class()
    store = store_cls.__new__(store_cls)
    store.renderChunkSize = 2  # two windows for three chunks
    store.doesCollectionExist = lambda modelName=None: True
    rows = {**dict(reversed(_rows('doc', 3).items())), **_rows('other', 1)}
    store.collectionObj = _FakeCollection(rows, {'doc-0': 'hello', 'doc-1': ' ', 'doc-2': 'world', 'other-0': 'skip'})
    rendered = []

    store.render('doc', rendered.append)

    assert rendered == ['hello ', 'world']
