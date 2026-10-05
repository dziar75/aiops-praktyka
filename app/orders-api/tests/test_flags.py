import json

from app import flags as flags_module
from app.config import settings


def test_file_section_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ERROR_RATE", "0.1")
    flags_file = tmp_path / "flags.json"
    flags_file.write_text(
        json.dumps({"orders-api": {"error_rate": 0.9, "cpu_burn": True, "feedback_text": "hi"}})
    )
    monkeypatch.setattr(settings, "flags_file", str(flags_file))

    store = flags_module.FlagStore()
    assert store.get("error_rate") == 0.9
    assert store.get("cpu_burn") is True
    assert store.get("feedback_text") == "hi"


def test_env_used_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SLOW_MENU_QUERY", "true")
    monkeypatch.setattr(settings, "flags_file", str(tmp_path / "missing.json"))

    store = flags_module.FlagStore()
    assert store.get("slow_menu_query") is True
    assert store.get("error_rate") == 0.0
