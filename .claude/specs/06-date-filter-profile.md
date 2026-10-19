# Spec: Date Filter Profile

## Overview
Step 6 adds a date-range filter to the profile page. Step 5 wired the profile's
summary stats, transaction list and category breakdown to live data, but they
always cover the user's entire history. This step lets a logged-in user narrow
all three sections to a chosen period, either with a custom start/end date or
with quick presets (This month, Last 3 months, All time). The filter is driven
by query-string parameters on the existing `GET /profile` route, so filtered
views are bookmarkable and need no new routes or JavaScript.

## Depends on
- Step 1: Database setup (`expenses.date` stored as `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Profile page UI
- Step 5: Backend connection (`database/queries.py` helpers and the `_build_*` functions in `app.py`)

## Routes
No new routes. The existing route gains optional query parameters:
- `GET /profile?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` — profile filtered to the inclusive date range — logged-in

Parameter behaviour:
- Both parameters are optional. Missing or empty means unbounded on that side.
- No parameters at all means "All time" (same output as Step 5).
- A value that does not parse as `YYYY-MM-DD` is ignored (treated as missing) and a
  flash message "Invalid date ignored." is shown. The page still returns 200.
- If `start_date` is after `end_date`, the two are swapped silently.

## Database changes
No database changes. Filtering uses the existing `expenses.date` column
(ISO `YYYY-MM-DD` text, so string comparison orders correctly).

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter bar between the profile card and the stats row: a
    `<form method="get" action="{{ url_for('profile') }}">` with two
    `<input type="date">` fields (`start_date`, `end_date`), pre-filled with the
    active values, and an "Apply" submit button.
  - Add preset links next to the form: "This month", "Last 3 months",
    "All time". Each is a plain `<a>` built with `url_for('profile', ...)`.
    The active preset (or "Custom" range) gets an `is-active` class.
  - Show the active range as a caption, e.g. "Showing 01 Oct 2026 – 19 Oct 2026"
    or "Showing all time".
  - Change the "Recent transactions" empty-state text to
    "No transactions in this period." when a filter is active.

## Files to change
- `database/queries.py` — add optional `start_date=None, end_date=None` keyword
  arguments to `get_summary_stats`, `get_recent_transactions` and
  `get_category_breakdown`. Append `AND date >= ?` / `AND date <= ?` only for
  bounds that are set. `get_user_by_id` is unchanged.
- `app.py` — in `profile()`, read and validate `start_date` / `end_date` from
  `request.args`, compute preset ranges, pass the dates through the
  `_build_stats`, `_build_transactions` and `_build_categories` helpers, and pass
  the filter state (`start_date`, `end_date`, `active_preset`, `range_label`,
  and the three preset URLs' date pairs) to the template.
- `templates/profile.html` — filter bar, presets, range caption (see above).
- `static/css/style.css` — styles for the filter bar (`.profile-filter`,
  `.filter-form`, `.filter-presets`, `.filter-preset`, `.filter-preset.is-active`,
  `.filter-range`), responsive at phone width.

## Files to create
- `tests/test_date_filter_profile.py` — tests for the filtered queries and route
  (written by the test-writer subagent from this spec).

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()`
- Parameterised queries only — dates are passed as `?` parameters; only the
  fixed `AND date >= ?` / `AND date <= ?` fragments may be concatenated into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles and no JavaScript; the filter works with a plain GET form
- Validate dates with `datetime.strptime(value, "%Y-%m-%d")`; never pass raw
  user input to SQL without validation
- Calling the query helpers with no date arguments must return exactly what
  Step 5 returned (existing tests in `tests/test_backend_connection.py` and
  `tests/test_profile.py` must still pass)
- Preset ranges, computed from `date.today()`:
  - This month: first day of the current month → today
  - Last 3 months: first day of the month two months back → today
  - All time: no parameters
- Category `pct` values must still sum to 100 for any non-empty filtered range
- Amounts always display with ₹

## Definition of done
- [ ] Logged in as demo@spendly.com, `/profile` with no parameters shows the
      same totals, count, transactions and categories as before this step
- [ ] The profile page shows a filter bar with Start date, End date, Apply, and
      the presets This month / Last 3 months / All time
- [ ] Picking a start and end date and clicking Apply reloads `/profile` with
      `?start_date=…&end_date=…` and the date inputs stay filled with those values
- [ ] With a range covering only some seed expenses, Total spent, Transactions,
      Top category, the transaction list and the category breakdown all reflect
      only expenses inside that range (inclusive of both end dates)
- [ ] Category percentages still add up to 100% for a filtered range
- [ ] A range with no expenses shows ₹0.00, 0 transactions, "—" top category,
      "No transactions in this period." and "No spending yet." with no errors
- [ ] Clicking "This month" filters to the current month and highlights that preset
- [ ] Clicking "All time" clears the filter and highlights that preset
- [ ] `/profile?start_date=not-a-date` returns 200, shows "Invalid date ignored."
      and behaves as if no start date were given
- [ ] `/profile?start_date=2026-10-20&end_date=2026-10-01` behaves the same as
      the swapped range
- [ ] Visiting `/profile?start_date=…` while logged out redirects to `/login`
- [ ] The filter bar has no horizontal scroll at phone width (≈375px)
- [ ] `pytest` passes, including the existing Step 5 tests
