# =============================================================================
# MIT License
# Copyright (c) 2026 Aparavi Software AG
# =============================================================================

"""Regression test for rendering a Weaviate document from its chunks."""

from __future__ import annotations

from .test_record_updates import _make_obj_records, _make_store


def test_render_returns_every_chunk(monkeypatch):
    """Render reads every chunk, in order, from a server that pages results like Weaviate does."""
    records = _make_obj_records('a', 2500, is_deleted=False)
    store, collection = _make_store(dict(reversed(records.items())))
    fetch = collection.query.fetch_objects

    # Weaviate returns QUERY_DEFAULTS_LIMIT (10) objects when no limit is given
    # and rejects offset + limit above QUERY_MAXIMUM_RESULTS (10000).
    def server_fetch(filters=None, limit=10, offset=0):
        assert offset + limit <= 10000, 'query maximum results exceeded'
        return fetch(filters=filters, limit=limit, offset=offset)

    monkeypatch.setattr(collection.query, 'fetch_objects', server_fetch)
    rendered = []
    store.render('a', rendered.append)

    assert ''.join(rendered) == ''.join(f'chunk {index}' for index in range(2500))
