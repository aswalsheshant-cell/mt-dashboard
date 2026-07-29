# qudify room-booking automation

Books meeting rooms on the qudify.co portal (Capital Cyberscape / Honasa) without
clicking through the grid by hand.

This is a standalone tool. It does not touch `dashboard/`, `scripts/` or
`PowerBI/` and has nothing to do with `data.js`.

---

## Setup (once)

```bash
cd tools/room-booking
pip install -r requirements.txt
playwright install chromium

cp config.example.json config.json      # edit booking_url, office, floor
python qudify_book.py login             # a browser opens - log in by hand
```

If corporate IT blocks `playwright install`, skip it and point the tool at a
Chrome you already have — set `chromium_executable` in `config.json` (or the
`QUDIFY_CHROMIUM` env var) to the browser binary.

`login` saves your cookies to `auth.json` (chmod 600, gitignored). Every later
run reuses it, so the script never has to know your password — this works whether
the portal uses SSO, a password form, or an emailed OTP. When bookings suddenly
start failing on a login page, the session expired: run `login` again.

## Tune it to the real page (once)

The selectors shipped in `config.example.json` are **educated guesses** — nobody
has the portal's HTML documented. Fix them with:

```bash
python qudify_book.py inspect --date 2026-07-31 --headed
```

It prints the room names it found, the background colours it saw and the state it
assigned to each, then writes a full dump and a screenshot to `artifacts/`.

Iterate until the output looks right:

- **No rooms listed** → fix `selectors.room_header`.
- **No cells / zero slots** → fix `selectors.slot_cell`.
- **A colour mapped to the wrong state** → copy its `rgb(...)` numbers into
  `palette` in `config.json`.

Cell state comes from the *rendered colour*, matching the on-page legend
(red = booked, green = selected, grey = not available, anything else = free), and
room columns are matched by *screen position*. Both survive front-end tweaks far
better than hardcoded CSS class names would.

## Book

Always dry-run first — it selects the cells, screenshots them, and stops before
submitting:

```bash
python qudify_book.py book --date 2026-07-31 --start 14:00 --duration 60 \
    --room "MT Team" --title "MT Review" --dry-run
```

Open the screenshot in `artifacts/`. If the right cells are highlighted, drop
`--dry-run` and run it for real.

Other shapes:

```bash
# whichever room on the floor is free
python qudify_book.py book --date tomorrow --start 10:00 --duration 90 --any-room

# 7 days out, by column number
python qudify_book.py book --date +7 --start 15:30 --duration 30 --room-index 3

# camp on a taken slot and grab it the moment it frees
python qudify_book.py watch --date +1 --start 11:00 --duration 60 \
    --room "MT Team" --interval 120 --max-minutes 240
```

`--date` takes `2026-07-31`, `today`, `tomorrow`, or `+N` days. `--start` takes
`14:00` or `"2:00 pm"`. `--duration` is minutes, in multiples of 30 (the grid's
slot size).

## Recurring bookings

Wrap it in cron (macOS/Linux) or Task Scheduler (Windows). To book the MT slot
7 days ahead, every weekday at 09:05:

```cron
5 9 * * 1-5 cd ~/mt-dashboard/tools/room-booking && \
  /usr/bin/python3 qudify_book.py book --date +7 --start 14:00 --duration 60 \
  --room "MT Team" --title "MT Review" >> cron.log 2>&1
```

Run it on a machine that is awake at that hour and can reach the portal — if
qudify is only reachable on the office network or VPN, a cloud VM will not work.

## Faster and sturdier: use the API

Clicking a grid is the slow path. The portal is a web app, so it has a JSON API
underneath. To find it:

```bash
python qudify_book.py capture      # browser opens; make ONE booking by hand
```

The requests land in `artifacts/network_log.json`. The `POST` that created the
booking is the one worth replaying directly — an API-based booker is faster and
much less fragile than driving the UI, which matters if you are racing others for
a slot the moment the booking window opens.

**`network_log.json` can contain auth tokens. It is gitignored — keep it that
way, and don't paste it anywhere public.** If you want the API version built,
share the *shape* of that POST (URL, field names) with the tokens redacted.

## Files

| File | |
|---|---|
| `qudify_book.py` | the tool |
| `config.example.json` | template — copy to `config.json` |
| `config.json` | your settings (gitignored) |
| `auth.json` | saved session (gitignored) |
| `artifacts/` | screenshots, dumps, network logs (gitignored) |

## Notes

- Meeting rooms are a shared resource, and a bot that camps on slots or books
  speculatively is the kind of thing IT tends to have an opinion about. Worth a
  word with whoever owns the portal before putting `watch` on a tight interval.
  `--interval` defaults to a polite 60s; don't drop it to single digits.
- Nothing here bypasses authentication — it drives the portal as you, with a
  session you created by logging in yourself.
- The script never deletes or edits existing bookings. It only selects free slots
  and confirms.
