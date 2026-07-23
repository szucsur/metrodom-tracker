import json
import os

import state


def test_load_seen_missing_file_returns_empty_set(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "nonexistent.json"))
    assert state.load_seen() == set()


def test_save_then_load_round_trip(tmp_path, monkeypatch):
    path = str(tmp_path / "seen.json")
    monkeypatch.setattr(state, "STATE_PATH", path)

    state.save_seen({"alberlet.hu:1", "rentola.hu:2"})
    assert state.load_seen() == {"alberlet.hu:1", "rentola.hu:2"}


def test_load_seen_corrupt_json_returns_empty_set(tmp_path, monkeypatch):
    path = tmp_path / "corrupt.json"
    path.write_text("not valid json")
    monkeypatch.setattr(state, "STATE_PATH", str(path))
    assert state.load_seen() == set()


def test_save_seen_caps_entries(tmp_path, monkeypatch):
    path = str(tmp_path / "seen.json")
    monkeypatch.setattr(state, "STATE_PATH", path)
    monkeypatch.setattr(state, "MAX_ENTRIES", 3)

    state.save_seen({f"source:{i}" for i in range(10)})
    with open(path) as f:
        saved = json.load(f)
    assert len(saved) == 3


def test_dedup_key_is_stable_and_source_scoped():
    from models import Listing

    a = Listing(source="alberlet.hu", listing_id="123", url="u", title="t")
    b = Listing(source="rentola.hu", listing_id="123", url="u", title="t")
    assert a.dedup_key() == "alberlet.hu:123"
    assert a.dedup_key() != b.dedup_key()
