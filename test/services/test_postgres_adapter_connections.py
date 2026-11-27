"""PostgreSQL adapters must close every connection on success and failure."""

from datetime import datetime, timezone
import pytest

from app.models.exception import HttpException
from app.security.adapters.postgres_ownership import PostgresOwnershipStore
from app.security.adapters.postgres_rate_limit import PostgresRateLimiter
from app.security.jwt_auth import AuthenticatedUser
from app.security.ownership import TaskOwnershipRecord


class FakeCursor:
    rowcount = 1

    def __init__(self, connection):
        self.connection = connection
        self.statement = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, *_args):
        self.statement = statement
        if self.connection.fail_execute:
            raise RuntimeError("database unavailable")

    def fetchone(self):
        if "SELECT task_id" in self.statement:
            return ("task-1", "user-1", "video", datetime.now(timezone.utc), {})
        return (1,)

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, *, fail_execute=False):
        self.fail_execute = fail_execute
        self.closed = False
        self.transaction_exited = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.transaction_exited = True
        return False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class FakeDriver:
    def __init__(self, *, fail_execute=False):
        self.connections = []
        self.fail_execute = fail_execute

    def connect(self, _dsn):
        connection = FakeConnection(fail_execute=self.fail_execute)
        self.connections.append(connection)
        return connection


def _ownership_store(driver):
    store = PostgresOwnershipStore.__new__(PostgresOwnershipStore)
    store.dsn = "postgresql://test"
    store._driver = driver
    return store


def _rate_limiter(driver):
    limiter = PostgresRateLimiter.__new__(PostgresRateLimiter)
    limiter.dsn = "postgresql://test"
    limiter._driver = driver
    from app.security.rate_limit import RateLimitConfig
    limiter.config = RateLimitConfig()
    return limiter


def test_ownership_store_closes_each_connection_after_operations():
    driver = FakeDriver()
    store = _ownership_store(driver)
    record = TaskOwnershipRecord(
        task_id="task-1", owner_id="user-1", created_at=datetime.now(timezone.utc),
        kind="video", metadata={},
    )

    store.create(record)
    store.get("task-1")
    store.list_for_owner("user-1")
    assert store.delete("task-1", "user-1") is True

    assert len(driver.connections) == 4
    assert all(connection.transaction_exited and connection.closed for connection in driver.connections)


def test_ownership_store_closes_connection_when_query_raises():
    driver = FakeDriver(fail_execute=True)
    store = _ownership_store(driver)

    with pytest.raises(RuntimeError, match="database unavailable"):
        store.create(TaskOwnershipRecord(
            task_id="task-1", owner_id="user-1", created_at=datetime.now(timezone.utc),
            kind="video", metadata={},
        ))

    assert len(driver.connections) == 1
    assert driver.connections[0].closed


def test_rate_limiter_closes_connection_after_each_counter_update():
    driver = FakeDriver()
    limiter = _rate_limiter(driver)
    user = AuthenticatedUser(sub="user-1")

    limiter.check_request(user, "request-1")
    limiter.check_generation(user, "request-2")

    assert len(driver.connections) == 2
    assert all(connection.transaction_exited and connection.closed for connection in driver.connections)


def test_rate_limiter_closes_connection_when_database_fails():
    driver = FakeDriver(fail_execute=True)
    limiter = _rate_limiter(driver)

    with pytest.raises(HttpException) as raised:
        limiter.check_request(AuthenticatedUser(sub="user-1"), "request-1")

    assert raised.value.status_code == 503
    assert len(driver.connections) == 1
    assert driver.connections[0].closed
