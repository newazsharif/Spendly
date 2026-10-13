# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly: a Flask + SQLite personal expense tracker (amounts in ₹). It is a step-by-step course scaffold: the front end exists, but the backend is mostly stubs marked "Step N" ("students will implement these").

## Commands

```bash
python3 -m venv venv && source venv/bin/activate   # venv/ is gitignored
pip install -r requirements.txt
python3 app.py                                     # dev server, debug mode, http://localhost:5001
pytest                                             # no tests exist yet
pytest tests/test_x.py::test_name                  # run a single test
```

No linter or build step is configured. There is no JS bundler or CSS framework.

## Architecture

- `app.py` is the single entry point: it creates the Flask app and defines all routes. Working routes (`/`, `/register`, `/login`, `/terms`, `/privacy`) only call `render_template`. Forms don't handle POST yet, and there are no sessions or auth.
- Placeholder routes return plain strings: `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`. Replace the stubs in place as each step is implemented.
- `database/db.py` is comments only. It is meant to provide `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (`CREATE TABLE IF NOT EXISTS`) and `seed_db()` (sample data). Nothing imports it yet.
- `templates/` uses Jinja2 inheritance: pages extend `base.html`, which provides the shared shell and `{% block %}` slots. Link with `url_for('<route function name>')`, so renaming a route function in `app.py` breaks template links.
- `static/css/style.css` holds all styling. `static/js/main.js` is an empty placeholder.
- `file.txt` is a pasted terminal transcript, not project code. Ignore it.
