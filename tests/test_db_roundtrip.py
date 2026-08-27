import sqlite3

import pytest
from cryptography.fernet import Fernet

import app
import db_crypto

_TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("RoleIQ_DB_KEY", _TEST_KEY)
    db_crypto._ephemeral_key = None
    db_crypto._warned_ephemeral = False
    yield
    db_crypto._ephemeral_key = None
    db_crypto._warned_ephemeral = False


def test_save_and_load_candidate_roundtrip():
    resume = "Jane Doe, 10 years of backend engineering experience."
    graph = {"candidate_summary": "Backend engineer", "roles": []}
    cid = app.save_candidate(resume, "Candidate", graph)

    loaded = app.load_candidate(cid)
    assert loaded["resume"] == resume
    assert loaded["experience_graph"] == '{"candidate_summary": "Backend engineer", "roles": []}'

    # Prove actual encryption at rest, not just transparent decrypt-on-read:
    # the raw column value on disk must not be the plaintext.
    raw = sqlite3.connect(app.DB_PATH).execute(
        "SELECT resume FROM candidates WHERE id=?", (cid,)
    ).fetchone()[0]
    assert resume not in raw


def test_save_candidate_upsert_dedups_by_content():
    resume = "Same resume text every time"
    cid1 = app.save_candidate(resume, "Candidate", {"v": 1})
    cid2 = app.save_candidate(resume, "Candidate", {"v": 2})
    assert cid1 == cid2

    count = sqlite3.connect(app.DB_PATH).execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    assert count == 1

    loaded = app.load_candidate(cid1)
    assert loaded["experience_graph"] == '{"v": 2}'


def test_save_session_roundtrip():
    history = [{"question": "Q1", "answer": "A1"}]
    app.save_session("sid1", "cid1", "Engineer", "ACME", "job description text",
                      {"role": "Engineer"}, {"company_context": []}, history)

    raw = sqlite3.connect(app.DB_PATH).execute(
        "SELECT history FROM sessions WHERE id=?", ("sid1",)
    ).fetchone()[0]
    decrypted = db_crypto.decrypt_text(raw)
    assert decrypted == '[{"question": "Q1", "answer": "A1"}]'


def test_missing_db_key_generates_ephemeral_key_and_warns(monkeypatch, caplog):
    monkeypatch.delenv("RoleIQ_DB_KEY", raising=False)
    db_crypto._ephemeral_key = None
    db_crypto._warned_ephemeral = False

    with caplog.at_level("WARNING", logger="roleiq"):
        encrypted = db_crypto.encrypt_text("some secret text")
    assert any("RoleIQ_DB_KEY" in r.message for r in caplog.records)

    # Still round-trips within the same run, against the cached ephemeral key.
    assert db_crypto.decrypt_text(encrypted) == "some secret text"


def test_wrong_db_key_fails_to_decrypt_clearly(monkeypatch):
    encrypted = db_crypto.encrypt_text("secret")
    monkeypatch.setenv("RoleIQ_DB_KEY", Fernet.generate_key().decode())
    with pytest.raises(db_crypto.DecryptionError, match="does not match"):
        db_crypto.decrypt_text(encrypted)
