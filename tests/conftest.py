import pytest

from support_copilot.data import load_export


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPPORT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("SUPPORT_NOW", raising=False)
    return tmp_path / "state"


@pytest.fixture(scope="session")
def export():
    return load_export()
