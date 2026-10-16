import re

import pytest

import app as app_module
from database import db, queries


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


DEMO_ID = 1


@pytest.fixture
def empty_user_id(client):
    return db.create_user("Empty User", "empty@spendly.com", "password123")


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


def test_get_user_by_id_valid(client):
    user = queries.get_user_by_id(DEMO_ID)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_missing(client):
    assert queries.get_user_by_id(9999) is None


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_shows_real_user(client):
    login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html


# ---- [SECTION 1: transaction history tests] ---------------------- #
def test_tx_demo_user_newest_first(client):
    txs = queries.get_recent_transactions(DEMO_ID)
    assert len(txs) == 8
    for t in txs:
        assert set(t) == {"date", "description", "category", "amount"}
    dates = [t["date"] for t in txs]
    assert dates == sorted(dates, reverse=True)
    assert txs[0]["description"] == "Gift"


def test_tx_limit_respected(client):
    assert len(queries.get_recent_transactions(DEMO_ID, limit=3)) == 3


def test_tx_empty_user(client, empty_user_id):
    assert queries.get_recent_transactions(empty_user_id) == []


def test_tx_profile_shows_rows(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    tbody = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert tbody.count("<tr>") == 8
    assert "₹1,999.00" in html
    assert html.index("Gift") < html.index("Lunch with team")


def test_tx_profile_empty_state(client, empty_user_id):
    login(client, "empty@spendly.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert "No transactions yet." in html


def test_tx_profile_isolation(client, empty_user_id):
    conn = db.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (empty_user_id, 42.50, "Food", "2026-10-02", "Solo coffee"),
    )
    conn.commit()
    conn.close()
    login(client, "empty@spendly.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert "Solo coffee" in html
    assert "₹42.50" in html
    assert "Headphones" not in html
# ---- [END SECTION 1] --------------------------------------------- #


# ---- [SECTION 2: summary stats tests] ---------------------------- #
def test_stats_demo_user(client):
    stats = queries.get_summary_stats(DEMO_ID)
    assert stats["total_spent"] == pytest.approx(5890.25)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Shopping"


def test_stats_empty_user(client, empty_user_id):
    assert queries.get_summary_stats(empty_user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_stats_profile_route_demo(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    assert "₹5,890.25" in html
    assert "Shopping" in html


def test_stats_profile_route_empty_user(client, empty_user_id):
    login(client, "empty@spendly.com", "password123")
    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "₹0.00" in html
    assert "—" in html
# ---- [END SECTION 2] --------------------------------------------- #


# ---- [SECTION 3: category breakdown tests] ----------------------- #
def test_cat_demo_breakdown(client):
    cats = queries.get_category_breakdown(DEMO_ID)
    assert len(cats) == 7
    assert cats[0]["name"] == "Shopping"
    amounts = [c["amount"] for c in cats]
    assert amounts == sorted(amounts, reverse=True)
    for c in cats:
        assert set(c) == {"name", "amount", "pct"}
        assert isinstance(c["pct"], int)
    assert sum(c["pct"] for c in cats) == 100


def test_cat_empty_user(client, empty_user_id):
    assert queries.get_category_breakdown(empty_user_id) == []


def test_cat_rounding_remainder(client, empty_user_id):
    conn = db.get_db()
    for category in ("Food", "Bills", "Health"):
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (empty_user_id, 10.0, category, "2026-10-01", "Equal " + category),
        )
    conn.commit()
    conn.close()
    cats = queries.get_category_breakdown(empty_user_id)
    assert len(cats) == 3
    assert sum(c["pct"] for c in cats) == 100
    assert sorted(c["pct"] for c in cats) == [33, 33, 34]


def test_cat_profile_shows_rows(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    assert html.count('class="cat-row"') == 7
    assert "bar-shopping" in html


def test_cat_profile_empty_state(client, empty_user_id):
    login(client, "empty@spendly.com", "password123")
    html = client.get("/profile").get_data(as_text=True)
    assert "No spending yet." in html


# ---- [END SECTION 3] --------------------------------------------- #
