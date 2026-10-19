import os
import re
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import queries
from database.db import create_user, get_db, get_user_by_email, get_user_by_id, init_db, seed_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error = None
    if not name:
        error = "Please enter your name."
    elif not EMAIL_RE.match(email):
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm_password:
        error = "Passwords do not match."
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "An account with this email already exists."

    if error:
        return render_template("register.html", error=error, name=name, email=email), 400

    flash("Registration successful! Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        error = "Please enter your email and password."
    else:
        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("profile"))

    return render_template("login.html", error=error, email=email), 400


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


CATEGORY_SLUGS = {"food", "transport", "bills", "health", "entertainment", "shopping", "other"}


def _cat_slug(category):
    slug = (category or "").lower()
    return slug if slug in CATEGORY_SLUGS else "other"


# ---- [SECTION 1: transaction history] ---------------------------- #
def _build_transactions(user_id, start_date=None, end_date=None):
    return [
        {
            "date": datetime.strptime(t["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": t["description"],
            "category": t["category"],
            "badge": "badge-" + _cat_slug(t["category"]),
            "amount": "{:,.2f}".format(t["amount"]),
        }
        for t in queries.get_recent_transactions(
            user_id, start_date=start_date, end_date=end_date
        )
    ]
# ---- [END SECTION 1] --------------------------------------------- #


# ---- [SECTION 2: summary stats] ---------------------------------- #
def _build_stats(user_id, start_date=None, end_date=None):
    stats = queries.get_summary_stats(user_id, start_date=start_date, end_date=end_date)
    return {
        "total_spent": "{:,.2f}".format(stats["total_spent"]),
        "transaction_count": stats["transaction_count"],
        "top_category": stats["top_category"],
    }
# ---- [END SECTION 2] --------------------------------------------- #


# ---- [SECTION 3: category breakdown] ----------------------------- #
def _build_categories(user_id, start_date=None, end_date=None):
    return [
        {
            "name": c["name"],
            "total": "{:,.2f}".format(c["amount"]),
            "percent": c["pct"],
            "bar": "bar-" + _cat_slug(c["name"]),
            "pct_class": "pct-%d" % (5 * round(c["pct"] / 5)),
        }
        for c in queries.get_category_breakdown(
            user_id, start_date=start_date, end_date=end_date
        )
    ]
# ---- [END SECTION 3] --------------------------------------------- #


# ---- [SECTION 4: date filter] ------------------------------------ #
PRESET_LABELS = {
    "this_month": "This month",
    "last_3_months": "Last 3 months",
    "all_time": "All time",
}


def _parse_date(value):
    """Return a date, None for an empty value, or raise ValueError."""
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _preset_ranges(today):
    year, month = today.year, today.month - 2
    if month <= 0:
        month += 12
        year -= 1
    return {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": (date(year, month, 1).isoformat(), today.isoformat()),
        "all_time": (None, None),
    }


def _range_label(start, end):
    fmt = "%d %b %Y"
    if start and end:
        return "Showing %s – %s" % (start.strftime(fmt), end.strftime(fmt))
    if start:
        return "Showing from %s" % start.strftime(fmt)
    if end:
        return "Showing up to %s" % end.strftime(fmt)
    return "Showing all time"
# ---- [END SECTION 4] --------------------------------------------- #


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = queries.get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    user["initials"] = "".join(w[0] for w in user["name"].split()[:2]).upper()

    invalid = False
    bounds = []
    for key in ("start_date", "end_date"):
        try:
            bounds.append(_parse_date(request.args.get(key, "").strip()))
        except ValueError:
            bounds.append(None)
            invalid = True
    if invalid:
        flash("Invalid date ignored.", "error")
    start, end = bounds
    if start and end and start > end:
        start, end = end, start

    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None
    presets = _preset_ranges(date.today())
    active_preset = next(
        (key for key, pair in presets.items() if pair == (start_iso, end_iso)), "custom"
    )

    return render_template(
        "profile.html",
        user=user,
        stats=_build_stats(user_id, start_iso, end_iso),
        transactions=_build_transactions(user_id, start_iso, end_iso),
        categories=_build_categories(user_id, start_iso, end_iso),
        start_date=start_iso or "",
        end_date=end_iso or "",
        active_preset=active_preset,
        range_label=_range_label(start, end),
        presets=[
            {"key": key, "label": PRESET_LABELS[key], "start": s, "end": e}
            for key, (s, e) in presets.items()
        ],
        is_filtered=bool(start_iso or end_iso),
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
