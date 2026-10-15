"""MongoDB circuit breaker: fail fast to the local fallback after a connection failure."""
import pytest
from pymongo.errors import DuplicateKeyError, PyMongoError, ServerSelectionTimeoutError

from config import database
from config.database import GuardedCollection


class FakeCollection:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    async def insert_one(self, doc):
        self.calls += 1
        if self.error:
            raise self.error
        return "ok"

    def find(self, query=None):
        self.calls += 1
        error = self.error

        class Cursor:
            def __aiter__(self):
                return self

            async def __anext__(self):
                if error:
                    raise error
                raise StopAsyncIteration
        return Cursor()


@pytest.fixture(autouse=True)
def reset():
    database.reset_mongo_breaker()
    yield
    database.reset_mongo_breaker()


@pytest.mark.asyncio
async def test_connection_failure_trips_breaker_and_later_calls_fail_fast():
    fake = FakeCollection(ServerSelectionTimeoutError("down"))
    coll = GuardedCollection(fake)
    with pytest.raises(PyMongoError):
        await coll.insert_one({})
    assert database.mongo_marked_down()
    with pytest.raises(PyMongoError):   # callers' existing fallback still catches this
        await coll.insert_one({})
    with pytest.raises(PyMongoError):
        coll.find({})
    assert fake.calls == 1              # the underlying driver was not called again


@pytest.mark.asyncio
async def test_cursor_iteration_failure_trips_breaker():
    coll = GuardedCollection(FakeCollection(ServerSelectionTimeoutError("down")))
    with pytest.raises(PyMongoError):
        [doc async for doc in coll.find({})]
    assert database.mongo_marked_down()


@pytest.mark.asyncio
async def test_ordinary_database_errors_do_not_trip_breaker():
    coll = GuardedCollection(FakeCollection(DuplicateKeyError("dup")))
    with pytest.raises(DuplicateKeyError):
        await coll.insert_one({})
    assert not database.mongo_marked_down()


@pytest.mark.asyncio
async def test_healthy_collection_passes_through():
    coll = GuardedCollection(FakeCollection())
    assert await coll.insert_one({}) == "ok"
    assert [doc async for doc in coll.find({})] == []
