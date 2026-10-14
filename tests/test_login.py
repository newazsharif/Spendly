import pytest

import app as app_module
from database import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def user_id(client):
    with client.session_transaction() as sess:
        return sess.get("user_id")


def test_get_login(client):
    assert client.get("/login").status_code == 200


def test_valid_login(client):
    resp = login(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    assert user_id(client) is not None


def test_email_case_and_whitespace(client):
    resp = login(client, email="  Demo@Spendly.com ")
    assert resp.status_code == 302
    assert user_id(client) is not None


@pytest.mark.parametrize(
    "email,password",
    [("demo@spendly.com", "wrongpass"), ("nobody@example.com", "demo123")],
)
def test_invalid_credentials(client, email, password):
    resp = login(client, email=email, password=password)
    assert resp.status_code == 400
    assert b"Invalid email or password." in resp.data
    assert user_id(client) is None


@pytest.mark.parametrize("email,password", [("", "demo123"), ("demo@spendly.com", "")])
def test_empty_fields(client, email, password):
    resp = login(client, email=email, password=password)
    assert resp.status_code == 400
    assert b"Please enter your email and password." in resp.data
    assert user_id(client) is None


def test_email_repopulated_password_not(client):
    resp = login(client, email="demo@spendly.com", password="wrongpass")
    assert b'value="demo@spendly.com"' in resp.data
    assert b"wrongpass" not in resp.data


def test_registration_flash_still_shows(client):
    client.post(
        "/register",
        data={
            "name": "Jane",
            "email": "jane@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    page = client.get("/login")
    assert b"Registration successful" in page.data


def test_navbar_state(client):
    page = client.get("/login")
    assert b"Sign in" in page.data
    assert b"Get started" in page.data
    assert b"Logout" not in page.data

    login(client)
    page = client.get("/")
    assert b"Logout" in page.data
    assert b"Get started" not in page.data
    assert b"Sign in" not in page.data


def test_logout(client):
    login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert user_id(client) is None


@pytest.mark.parametrize("path", ["/login", "/register"])
def test_logged_in_redirected(client, path):
    login(client)
    assert client.get(path).headers["Location"].endswith("/")
    assert client.post(path, data={}).status_code == 302


def test_landing_ctas_hidden_when_logged_in(client):
    page = client.get("/")
    assert b"Create free account" in page.data
    assert b"Ready to take control?" in page.data

    login(client)
    page = client.get("/")
    assert b"Create free account" not in page.data
    assert b"Ready to take control?" not in page.data
