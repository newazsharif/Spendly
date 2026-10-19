import re
from datetime import date

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


def login(client):
    return client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})


def demo_id():
    conn = db.get_db()
    try:
        return conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()["id"]
    finally:
        conn.close()


TODAY = date.today()
D1 = TODAY.replace(day=1).isoformat()
D8 = TODAY.replace(day=8).isoformat()
D5 = TODAY.replace(day=5).isoformat()
D3 = TODAY.replace(day=3).isoformat()
D2 = TODAY.replace(day=2).isoformat()
D9 = TODAY.replace(day=9).isoformat()
EMPTY_START, EMPTY_END = "2000-01-01", "2000-01-31"


def stat_values(html):
    return [v.strip() for v in re.findall(r'class="profile-stat-value"[^>]*>(.*?)</', html, re.S)]


def active_presets(html):
    return [m.strip() for m in re.findall(r'class="filter-preset is-active"[^>]*>(.*?)</a>', html, re.S)]


def fmt(iso):
    return date.fromisoformat(iso).strftime("%d %b %Y")


# ---------- query helpers ----------

def test_summary_both_bounds_filters_to_days_1_to_8(client):
    s = queries.get_summary_stats(demo_id(), start_date=D1, end_date=D8)
    assert s["total_spent"] == pytest.approx(3020.50)
    assert s["transaction_count"] == 4
    assert s["top_category"] == "Bills"


def test_summary_no_args_is_all_time(client):
    s = queries.get_summary_stats(demo_id())
    assert s["total_spent"] == pytest.approx(5890.25)
    assert s["transaction_count"] == 8
    assert s["top_category"] == "Shopping"


def test_summary_explicit_none_equals_no_args(client):
    uid = demo_id()
    assert queries.get_summary_stats(uid, start_date=None, end_date=None) == queries.get_summary_stats(uid)


def test_summary_start_only(client):
    # from day 12 onward: 12, 16, 20, 25 => total - 3020.50 minus days 1..8 minus nothing between
    s = queries.get_summary_stats(demo_id(), start_date=TODAY.replace(day=9).isoformat())
    assert s["transaction_count"] == 4
    assert s["total_spent"] == pytest.approx(5890.25 - 3020.50)


def test_summary_end_only(client):
    s = queries.get_summary_stats(demo_id(), end_date=D8)
    assert s["transaction_count"] == 4
    assert s["total_spent"] == pytest.approx(3020.50)


def test_summary_empty_range_is_zero(client):
    s = queries.get_summary_stats(demo_id(), start_date=EMPTY_START, end_date=EMPTY_END)
    assert s["total_spent"] == 0
    assert s["transaction_count"] == 0
    assert s["top_category"] == "—"


def test_summary_bounds_inclusive_single_day(client):
    s = queries.get_summary_stats(demo_id(), start_date=D1, end_date=D1)
    assert s["transaction_count"] == 1
    assert s["total_spent"] == pytest.approx(450.00)
    s8 = queries.get_summary_stats(demo_id(), start_date=D8, end_date=D8)
    assert s8["transaction_count"] == 1


def test_summary_range_excluding_boundary_days(client):
    s = queries.get_summary_stats(demo_id(), start_date=D2, end_date=D5)
    assert s["transaction_count"] == 2  # days 3 and 5


def test_transactions_filtered_by_range(client):
    rows = queries.get_recent_transactions(demo_id(), start_date=D1, end_date=D8)
    assert len(rows) == 4
    assert all(D1 <= r["date"] <= D8 for r in rows)


def test_transactions_inclusive_bounds_present(client):
    rows = queries.get_recent_transactions(demo_id(), start_date=D1, end_date=D8)
    dates = {r["date"] for r in rows}
    assert D1 in dates and D8 in dates


def test_transactions_empty_range(client):
    assert queries.get_recent_transactions(demo_id(), start_date=EMPTY_START, end_date=EMPTY_END) == []


def test_transactions_no_args_equals_unfiltered(client):
    uid = demo_id()
    assert queries.get_recent_transactions(uid, start_date=None, end_date=None) == queries.get_recent_transactions(uid)
    assert len(queries.get_recent_transactions(uid)) == 8


def test_transactions_start_only_and_end_only(client):
    uid = demo_id()
    assert len(queries.get_recent_transactions(uid, start_date=D9)) == 4
    assert len(queries.get_recent_transactions(uid, end_date=D8)) == 4


def test_categories_filtered_by_range(client):
    cats = queries.get_category_breakdown(demo_id(), start_date=D1, end_date=D8)
    amounts = {c["name"]: c["amount"] for c in cats}
    assert amounts == {"Food": 450.00, "Transport": 120.50, "Bills": 1800.00, "Health": 650.00}


def test_categories_pct_sums_to_100_when_filtered(client):
    cats = queries.get_category_breakdown(demo_id(), start_date=D1, end_date=D8)
    assert sum(c["pct"] for c in cats) == 100


def test_categories_pct_sums_to_100_start_only(client):
    cats = queries.get_category_breakdown(demo_id(), start_date=D9)
    assert cats and sum(c["pct"] for c in cats) == 100


def test_categories_empty_range(client):
    assert queries.get_category_breakdown(demo_id(), start_date=EMPTY_START, end_date=EMPTY_END) == []


def test_categories_no_args_equals_unfiltered(client):
    uid = demo_id()
    assert queries.get_category_breakdown(uid, start_date=None, end_date=None) == queries.get_category_breakdown(uid)


def test_filtered_helpers_do_not_leak_other_users(client):
    other = db.create_user("Other", "other@example.com", "pw12345")
    s = queries.get_summary_stats(other, start_date=D1, end_date=D8)
    assert s["transaction_count"] == 0


# ---------- route ----------

def test_profile_logged_out_with_params_redirects_to_login(client):
    resp = client.get(f"/profile?start_date={D1}&end_date={D8}")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_no_params_shows_all_time(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    vals = stat_values(html)
    assert "₹5,890.25" in vals[0]
    assert vals[1] == "8"
    assert vals[2] == "Shopping"
    assert active_presets(html) == ["All time"]
    assert "Showing all time" in html


def test_profile_has_filter_form_and_presets(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    assert 'name="start_date"' in html and 'name="end_date"' in html
    assert 'type="date"' in html
    assert "Apply" in html
    for label in ("This month", "Last 3 months", "All time"):
        assert label in html


def test_profile_custom_range_filters_stats(client):
    login(client)
    resp = client.get(f"/profile?start_date={D1}&end_date={D8}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    vals = stat_values(html)
    assert "₹3,020.50" in vals[0]
    assert vals[1] == "4"
    assert vals[2] == "Bills"


def test_profile_custom_range_filters_transactions_and_categories(client):
    login(client)
    html = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    assert html.count('class="cat-row"') == 4
    # Shopping (outside range) must not appear in the filtered views
    assert "Shopping" not in html
    assert "₹1,800.00" in html


def test_profile_custom_range_prefills_inputs(client):
    login(client)
    html = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    assert f'value="{D1}"' in html
    assert f'value="{D8}"' in html


def test_profile_custom_range_caption(client):
    login(client)
    html = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    m = re.search(r'class="filter-range"[^>]*>(.*?)</p>', html, re.S)
    assert m
    assert fmt(D1) in m.group(1) and fmt(D8) in m.group(1)
    assert "Showing" in m.group(1)


def test_profile_empty_range_shows_zero_state(client):
    login(client)
    resp = client.get(f"/profile?start_date={EMPTY_START}&end_date={EMPTY_END}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    vals = stat_values(html)
    assert "₹0.00" in vals[0]
    assert vals[1] == "0"
    assert vals[2] == "—"
    assert "No transactions in this period." in html
    assert "No spending yet." in html


def test_profile_no_filter_has_no_period_empty_text(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    assert "No transactions in this period." not in html


def test_profile_invalid_start_date_ignored_with_notice(client):
    login(client)
    resp = client.get("/profile?start_date=not-a-date")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid date ignored." in html
    vals = stat_values(html)
    assert "₹5,890.25" in vals[0]
    assert vals[1] == "8"


def test_profile_invalid_end_date_ignored_with_notice(client):
    login(client)
    resp = client.get("/profile?end_date=2026-13-45")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid date ignored." in html
    assert stat_values(html)[1] == "8"


def test_profile_invalid_start_with_valid_end_acts_as_end_only(client):
    login(client)
    html = client.get(f"/profile?start_date=garbage&end_date={D8}").get_data(as_text=True)
    assert "Invalid date ignored." in html
    assert stat_values(html)[1] == "4"


def test_profile_valid_dates_show_no_invalid_notice(client):
    login(client)
    html = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    assert "Invalid date ignored." not in html


def test_profile_empty_params_treated_as_missing_without_notice(client):
    login(client)
    html = client.get("/profile?start_date=&end_date=").get_data(as_text=True)
    assert "Invalid date ignored." not in html
    assert stat_values(html)[1] == "8"


def test_profile_swapped_range_equals_ordered_range(client):
    login(client)
    ordered = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    swapped = client.get(f"/profile?start_date={D8}&end_date={D1}").get_data(as_text=True)
    assert stat_values(swapped) == stat_values(ordered)
    assert swapped.count('class="cat-row"') == ordered.count('class="cat-row"')
    assert "Invalid date ignored." not in swapped


def test_profile_this_month_preset_highlighted(client):
    login(client)
    first = TODAY.replace(day=1).isoformat()
    html = client.get(f"/profile?start_date={first}&end_date={TODAY.isoformat()}").get_data(as_text=True)
    assert active_presets(html) == ["This month"]


def test_profile_this_month_preset_link_points_to_month_range(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    m = re.search(r'<a[^>]*href="([^"]*)"[^>]*>\s*This month\s*</a>', html, re.S)
    assert m
    href = m.group(1).replace("&amp;", "&")
    assert f"start_date={TODAY.replace(day=1).isoformat()}" in href
    assert f"end_date={TODAY.isoformat()}" in href


def test_profile_last_3_months_preset_link(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    m = re.search(r'<a[^>]*href="([^"]*)"[^>]*>\s*Last 3 months\s*</a>', html, re.S)
    assert m
    month = TODAY.month - 2
    year = TODAY.year
    if month < 1:
        month += 12
        year -= 1
    href = m.group(1).replace("&amp;", "&")
    assert f"start_date={date(year, month, 1).isoformat()}" in href
    assert f"end_date={TODAY.isoformat()}" in href


def test_profile_all_time_link_has_no_params(client):
    login(client)
    html = client.get("/profile").get_data(as_text=True)
    m = re.search(r'<a[^>]*href="([^"]*)"[^>]*>\s*All time\s*</a>', html, re.S)
    assert m
    assert "start_date" not in m.group(1) and "end_date" not in m.group(1)


def test_profile_custom_range_not_marked_all_time(client):
    login(client)
    html = client.get(f"/profile?start_date={D1}&end_date={D8}").get_data(as_text=True)
    assert "All time" not in active_presets(html)


def test_template_has_no_hex_or_inline_styles():
    with open("templates/profile.html") as f:
        src = f.read()
    assert "style=" not in src
    assert "#" not in src
