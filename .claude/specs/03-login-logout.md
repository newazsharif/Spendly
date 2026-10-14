# Spec: Login and Logout

## Overview
Make the existing `/login` form functional and implement `/logout`. A visitor submits email and password; the server looks the user up, verifies the password hash with werkzeug, and stores the user's id in the Flask `session`. Logout clears the session. The navbar reflects auth state. This is Step 3 of the roadmap: registration (Step 2) deliberately did not log users in, so this step introduces sessions.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`)
- Step 2 — Registration (`get_user_by_email()` in `database/db.py`, `app.secret_key` already configured, registration redirects to `/login` with a flashed success message)

## Routes
- `GET /login` — render the login form (already exists); redirect to `/` if already logged in — public
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to `/` on success; re-render the form with an error (HTTP 400) on failure — public
- `GET /logout` — clear the session, flash a message, redirect to `/login` (replaces the "Step 3" stub) — logged-in

`/login` and `/logout` use the existing `login()` and `logout()` view functions. No new route functions.

## Database changes
No database changes. Reuse `get_user_by_email(email)` from `database/db.py`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"`; re-populate `email` on error (never the password); keep the existing flash and `{% if error %}` blocks
  - `templates/base.html` — navbar: when `session.get('user_id')` is set, show a "Logout" link (`url_for('logout')`) instead of "Sign in" / "Get started"

## Files to change
- `app.py` — import `session`, `check_password_hash`; implement POST in `login()` (add `methods=["GET", "POST"]`); implement `logout()`
- `templates/login.html` — form action and email re-population
- `templates/base.html` — auth-aware navbar
- `templates/landing.html` — handle "Create free account" button and reagarding section not to visible when user logged in

## Files to create
- `tests/test_login.py` — pytest tests for login and logout (uses a temporary DB)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`check_password_hash` to verify); never store or log plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Link with `url_for('<route function name>')`; do not rename existing route functions
- Strip and lowercase the email before lookup
- Use one generic error for unknown email and wrong password: "Invalid email or password." (no user enumeration)
- Empty email or password shows a validation error
- On failure return HTTP 400 with the form re-rendered (matches `register()`); on success `redirect(url_for('/'))`
- Store only `user_id` in the session; call `session.clear()` on logout (and before setting a new login)
- Always close DB connections (`try/finally`), matching `database/db.py`
- Do not add route protection for other pages (later steps)

## Definition of done
- [ ] `GET /login` renders the form
- [ ] Logging in as `demo@spendly.com` / `demo123` redirects to `/` and sets the session
- [ ] Email casing/whitespace does not matter (`  Demo@Spendly.com `works)
- [ ] Wrong password and unknown email both show "Invalid email or password." with status 400 and no session
- [ ] Empty email or password shows an error and no session is created
- [ ] On error the email field keeps its value; the password field is empty
- [ ] The "Registration successful" flash still appears on `/login` after registering
- [ ] Navbar shows "Logout" when logged in, and "Sign in" / "Get started" when logged out
- [ ] `GET /logout` clears the session and redirects to `/login`
- [ ] `GET /login` and `GET /register` should not be accessable while user logged in already
- [ ] "Create free account" button and reagarding section should not be visible while user logged in and design have to done accordingly
- [ ] Visiting `/login` while logged in redirects to `/`
- [ ] `pytest tests/test_login.py` passes
