import pytest

from bridgescope.api import dependencies


class FakeSession:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self) -> "FakeSession":
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.exited = True


def test_get_db_session_yields_and_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(dependencies, "SessionLocal", lambda: fake_session)

    session_generator = dependencies.get_db_session()
    session = next(session_generator)

    assert session is fake_session
    assert fake_session.entered is True
    assert fake_session.exited is False

    with pytest.raises(StopIteration):
        next(session_generator)

    assert fake_session.exited is True

