import os
import re
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

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


# Hardcoded until Step 5 wires the profile page to the database.
PROFILE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "member_since": "January 2026",
}

PROFILE_TRANSACTIONS = [
    {"date": "12 Oct 2026", "description": "Lunch with team", "category": "Food", "badge": "badge-food", "amount": "450.00"},
    {"date": "10 Oct 2026", "description": "Metro card recharge", "category": "Transport", "badge": "badge-transport", "amount": "120.50"},
    {"date": "08 Oct 2026", "description": "Electricity bill", "category": "Bills", "badge": "badge-bills", "amount": "1,800.00"},
    {"date": "05 Oct 2026", "description": "Pharmacy", "category": "Health", "badge": "badge-health", "amount": "650.00"},
    {"date": "03 Oct 2026", "description": "Movie tickets", "category": "Entertainment", "badge": "badge-entertainment", "amount": "350.00"},
    {"date": "01 Oct 2026", "description": "Headphones", "category": "Shopping", "badge": "badge-shopping", "amount": "1,999.00"},
]

PROFILE_CATEGORIES = [
    {"name": "Shopping", "total": "1,999.00", "percent": 33, "bar": "bar-shopping"},
    {"name": "Bills", "total": "1,800.00", "percent": 30, "bar": "bar-bills"},
    {"name": "Health", "total": "650.00", "percent": 11, "bar": "bar-health"},
    {"name": "Food", "total": "450.00", "percent": 7, "bar": "bar-food"},
    {"name": "Entertainment", "total": "350.00", "percent": 6, "bar": "bar-entertainment"},
]
for _cat in PROFILE_CATEGORIES:
    _cat["pct_class"] = "pct-%d" % (5 * round(_cat["percent"] / 5))

PROFILE_STATS = {
    "total_spent": "5,369.50",
    "transaction_count": len(PROFILE_TRANSACTIONS),
    "top_category": PROFILE_CATEGORIES[0]["name"],
}


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = dict(PROFILE_USER)
    user["initials"] = "".join(w[0] for w in user["name"].split()[:2]).upper()
    return render_template(
        "profile.html",
        user=user,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        categories=PROFILE_CATEGORIES,
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
