# Spec: Registration

## Overview
Make the existing `/register` form functional so a visitor can create a Spendly account. The route accepts the form POST, validates input, hashes the password, inserts a row into `users`, show registration successfull message and redirects to the login page. This is the first auth feature on the roadmap; login, sessions and logout come in Step 3, so registration deliberately does not log the user in.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`, `init_db()` in `database/db.py`)

## Routes
- `GET /register` — render the registration form (already exists) — public
- `POST /register` — validate form, create user, redirect to `/login` on success; re-render the form with an error on failure — public

Both methods are handled by the existing `register()` view in `app.py` (`methods=["GET", "POST"]`). No new route functions.

## Database changes
No database changes. The existing `users` table already has `name`, `email` (UNIQUE), `password_hash` and `created_at`. Add a helper in `database/db.py` (no schema change):
- `create_user(name, email, password)` — hashes the password with `generate_password_hash`, inserts with a parameterised query, returns the new user id; raises `sqlite3.IntegrityError` on duplicate email (caller handles it).
- `get_user_by_email(email)` — optional helper for a pre-check; the UNIQUE constraint remains the source of truth.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — change `action="/register"` to `action="{{ url_for('register') }}"`; re-populate `name` and `email` values on error (never the password); keep the existing `{% if error %}` block. add the confirm password field and match with the password field, confirm both are same.

## Files to change
- `app.py` — import `request`, `redirect`, `url_for`; implement POST handling in `register()`
- `database/db.py` — add `create_user` (and optionally `get_user_by_email`)
- `templates/register.html` — form action and value re-population

## Files to create
- `tests/test_registration.py` — pytest tests for the registration flow (uses a temporary DB)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log plaintext
- Use CSS variables — never hardcode hex values (reuse existing `.auth-error`, `.form-input` styles; add to `static/css/style.css` only if needed, using variables)
- All templates extend `base.html`
- Link with `url_for('<route function name>')`; do not rename existing route functions
- Server-side validation (do not rely on HTML `required`):
  - name: non-empty after strip
  - email: non-empty, stripped, lowercased, contains `@` with a basic format check
  - password: at least 8 characters
  - confirm password: must equal password
- Duplicate email shows a friendly error ("An account with this email already exists") by catching `sqlite3.IntegrityError`; do not leak other DB errors
- Always close DB connections (`try/finally`), matching the style in `database/db.py`
- On validation failure return HTTP 400 with the form re-rendered; on success `redirect(url_for('login'))`
- Do not add sessions or auto-login (Step 3)

## Definition of done
- [ ] `GET /register` still renders the form
- [ ] Submitting valid name, email and an 8+ character password redirects to `/login`
- [ ] A new row appears in `users` with the email lowercased and `password_hash` starting with a werkzeug hash prefix (not the plaintext password)
- [ ] Registering the same email again (also with different casing) shows "An account with this email already exists" and creates no second row
- [ ] A password shorter than 8 characters shows an error and creates no user
- [ ] Empty/whitespace-only name or an invalid email shows an error and creates no user
- [ ] On error the name and email fields keep their values; the password field is empty
- [ ] A confirm password that differs from the password shows "Passwords do not match." and creates no user
- [ ] The demo user `demo@spendly.com` cannot be re-registered
- [ ] `pytest tests/test_registration.py` passes
