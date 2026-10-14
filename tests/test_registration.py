import sqlite3

import pytest
from werkzeug.security import check_password_hash

import app as app_module
from database import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def count_users(email=None):
    conn = db.get_db()
    try:
        if email:
            return conn.execute(
                "SELECT COUNT(*) FROM users WHERE lower(email) = ?", (email.lower(),)
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def post(client, name="Jane Doe", email="Jane@Example.com", password="password123",
         confirm_password=None):
    if confirm_password is None:
        confirm_password = password
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": confirm_password,
        },
    )


def test_get_register(client):
    assert client.get("/register").status_code == 200


def test_valid_registration(client):
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    row = db.get_user_by_email("jane@example.com")
    assert row is not None
    assert row["password_hash"] != "password123"
    assert check_password_hash(row["password_hash"], "password123")

    page = client.get("/login")
    assert b"Registration successful" in page.data


def test_duplicate_email(client):
    post(client)
    before = count_users()
    resp = post(client, email="JANE@example.com")
    assert resp.status_code == 400
    assert b"An account with this email already exists" in resp.data
    assert count_users() == before


def test_demo_email_rejected(client):
    before = count_users()
    resp = post(client, email="demo@spendly.com")
    assert resp.status_code == 400
    assert count_users() == before


@pytest.mark.parametrize(
    "kwargs",
    [
        {"password": "short"},
        {"name": "   "},
        {"email": "not-an-email"},
    ],
)
def test_invalid_input(client, kwargs):
    before = count_users()
    resp = post(client, **kwargs)
    assert resp.status_code == 400
    assert count_users() == before


def test_password_mismatch(client):
    before = count_users()
    resp = post(client, password="password123", confirm_password="password124")
    assert resp.status_code == 400
    assert b"Passwords do not match." in resp.data
    assert count_users() == before


def test_missing_confirm_field(client):
    before = count_users()
    resp = client.post(
        "/register",
        data={"name": "Jane Doe", "email": "jane@example.com", "password": "password123"},
    )
    assert resp.status_code == 400
    assert count_users() == before


def test_form_repopulated_on_error(client):
    resp = post(
        client,
        name="Jane Doe",
        email="jane@example.com",
        password="hunter2hunter2",
        confirm_password="different-pass",
    )
    assert resp.status_code == 400
    assert b'value="Jane Doe"' in resp.data
    assert b'value="jane@example.com"' in resp.data
    assert b"hunter2hunter2" not in resp.data
    assert b"different-pass" not in resp.data
