# =============================================================================
# MIT License
# Copyright (c) 2026 Aparavi Software AG
# =============================================================================

"""Elasticsearch store: render returns every chunk of a stored document.

The client is a stand-in that rejects a search the way Elasticsearch does when
its size is above index.max_result_window (10000 by default).
"""

import sys
import types

import pytest

from ai.common.config import Config

STORE_MODULE = 'nodes.store_elasticsearch.elasticsearch_store'
SERVER_RESULT_WINDOW = 10000


class ResultWindowTooLarge(Exception):
    """Stands in for the BadRequestError that Elasticsearch returns."""


class FakeElasticsearch:
    """One index that holds the chunks of one object."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.chunks: list[str] = []
        self.indices = types.SimpleNamespace(exists=lambda index: True)

    def search(self, index: str, body: dict) -> dict:
        if body['size'] > SERVER_RESULT_WINDOW:
            raise ResultWindowTooLarge(body['size'])
        chunk_range = body['query']['bool']['must'][1]['range']['meta.chunkId']
        chunk_ids = range(chunk_range['gte'], min(chunk_range['lt'], len(self.chunks)))
        return {'hits': {'hits': [{'_source': {'content': self.chunks[i], 'meta': {'chunkId': i}}} for i in chunk_ids]}}


@pytest.fixture
def store_class(monkeypatch: pytest.MonkeyPatch) -> type:
    """Install the stand-in client modules and return the store class loaded against them.

    Args:
        monkeypatch (pytest.MonkeyPatch): installs the stand-ins and restores the real modules afterwards.
    """
    elasticsearch = types.ModuleType('elasticsearch')
    elasticsearch.Elasticsearch = FakeElasticsearch
    helpers = types.ModuleType('elasticsearch.helpers')
    helpers.bulk = helpers.scan = None
    helpers.BulkIndexError = type('BulkIndexError', (Exception,), {})

    import nodes.store_elasticsearch as package

    # Same isolation as test_elasticsearch_credentials.py: restore the package attribute and the
    # sys.modules entries, so later tests never get the module bound to these stand-ins.
    monkeypatch.setattr(package, 'elasticsearch_store', getattr(package, 'elasticsearch_store', None), raising=False)
    monkeypatch.setitem(sys.modules, 'elasticsearch', elasticsearch)
    monkeypatch.setitem(sys.modules, 'elasticsearch.helpers', helpers)
    monkeypatch.setitem(sys.modules, STORE_MODULE, sys.modules.get(STORE_MODULE))
    del sys.modules[STORE_MODULE]
    monkeypatch.setattr(Config, 'getNodeConfig', staticmethod(lambda provider, conn_config: {'index': 'docs'}))
    from nodes.store_elasticsearch.elasticsearch_store import Store

    return Store


def test_render_returns_a_document_longer_than_the_result_window(store_class: type) -> None:
    """With the default renderChunkSize, render reads the document in windows the server accepts."""
    store = store_class('elasticsearch', {}, {})
    store.client.chunks = [f'[{i}]' for i in range(SERVER_RESULT_WINDOW + 500)]

    rendered: list[str] = []
    store.render('object', rendered.append)

    assert ''.join(rendered) == ''.join(store.client.chunks)
