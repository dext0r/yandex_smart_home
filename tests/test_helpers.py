from . import MockCacheStore, MockStore


async def test_async_load():
    cache = MockCacheStore()
    assert cache._data == {"attrs": {}}

    await cache.async_load()
    assert cache._data == {"attrs": {}}

    cache._store = MockStore({"foo": "bar"})
    await cache.async_load()
    assert cache._data == {"foo": "bar"}


async def test_cache():
    cache = MockCacheStore()
    assert cache.get_attr_value("foo", "bar") is None

    cache.save_attr_value("foo", "bar", ["buz"])
    cache._store.async_delay_save.assert_called_once()
    cache._store.async_delay_save.reset_mock()

    cache.save_attr_value("foo", "bar", ["buz"])
    cache._store.async_delay_save.assert_not_called()

    cache.save_attr_value("foo", "bar", [1, 2, 3])
    cache._store.async_delay_save.assert_called_once()
    assert cache.get_attr_value("foo", "bar") == [1, 2, 3]
