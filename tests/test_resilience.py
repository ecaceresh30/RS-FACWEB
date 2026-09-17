import httpx
import pytest

from app.resilience import with_retry


def test_with_retry_retries_transient_errors_then_succeeds():
    calls = {"count": 0}

    @with_retry
    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise httpx.ConnectError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3


def test_with_retry_gives_up_after_max_attempts():
    calls = {"count": 0}

    @with_retry
    def always_flaky():
        calls["count"] += 1
        raise httpx.ConnectError("boom")

    with pytest.raises(httpx.ConnectError):
        always_flaky()

    assert calls["count"] == 3


def test_with_retry_does_not_retry_non_transient_errors():
    calls = {"count": 0}

    @with_retry
    def always_fails():
        calls["count"] += 1
        raise ValueError("not transient")

    with pytest.raises(ValueError):
        always_fails()

    assert calls["count"] == 1
