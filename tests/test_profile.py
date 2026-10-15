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


def login(client):
    return client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(client):
    login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "demo@spendly.com" in html
    assert "Total spent" in html and "Transactions" in html and "Top category" in html
    assert html.count('class="badge ') >= 3
    assert html.count('class="cat-row"') >= 3


def test_navbar_shows_name_and_logout(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    assert 'class="nav-user"' in html
    assert "Logout" in html


def test_template_has_no_hex_or_inline_styles():
    with open("templates/profile.html") as f:
        src = f.read()
    assert "style=" not in src
    assert "#" not in src
