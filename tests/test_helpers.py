from . import MockCacheStore, MockStore


async def test_async_load() -> None:
    cache = MockCacheStore()
    assert cache._data == {"attrs": {}}

    await cache.async_load()
    assert cache._data == {"attrs": {}}

    cache._store = MockStore({"foo": {"bar": "buz"}})
    await cache.async_load()
    assert cache._data == {"foo": {"bar": "buz"}}


async def test_cache() -> None:
    cache = MockCacheStore()
    assert cache.get_attr_value("foo", "bar") is None

    cache.save_attr_value("foo", "bar", ["buz"])
    cache._store.saved_mock.assert_called_once()
    cache._store.saved_mock.reset_mock()

    cache.save_attr_value("foo", "bar", ["buz"])
    cache._store.saved_mock.assert_not_called()

    cache.save_attr_value("foo", "bar", [1, 2, 3])
    cache._store.saved_mock.assert_called_once()
    assert cache.get_attr_value("foo", "bar") == [1, 2, 3]
