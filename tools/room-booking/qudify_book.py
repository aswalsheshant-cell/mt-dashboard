#!/usr/bin/env python3
"""
Automate meeting-room booking on qudify.co (Honasa office booking portal).

The portal renders a grid: room names across the top, 30-minute time slots down
the side. A cell's colour tells you its state (the on-page legend: red = booked,
green = selected, grey = not available). This script drives that grid with
Playwright.

Because the page's HTML classes are not documented anywhere, cell state is
detected from the *rendered background colour* rather than from CSS class names,
and room columns are matched by *horizontal position* rather than by DOM nesting.
That keeps the automation working across minor front-end changes.

Commands
--------
  login     Open a real browser, you log in by hand, the session is saved.
  inspect   Dump the grid (rooms, slots, colours) so selectors/colours can be tuned.
  capture   Record network traffic while you book once by hand -> reveals the API.
  book      Book a slot.
  watch     Poll until a slot becomes free, then book it.

Quick start
-----------
  pip install -r requirements.txt
  playwright install chromium
  cp config.example.json config.json     # edit base_url, office, floor
  python qudify_book.py login
  python qudify_book.py inspect --date 2026-07-31
  python qudify_book.py book --date 2026-07-31 --start 14:00 --duration 60 \
      --room "MT Team" --title "MT Review" --dry-run

Drop --dry-run once the dry run's screenshot shows the right cells selected.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import sync_playwright, Page, Locator, TimeoutError as PWTimeout
except ImportError:  # pragma: no cover - guidance for a fresh machine
    sys.exit(
        "Playwright is not installed.\n"
        "  pip install -r requirements.txt\n"
        "  playwright install chromium"
    )

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "config.json"
EXAMPLE_CONFIG = HERE / "config.example.json"

SLOT_MINUTES = 30  # the grid's granularity


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #

def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        if EXAMPLE_CONFIG.exists():
            sys.exit(
                f"No config at {path}.\n"
                f"  cp {EXAMPLE_CONFIG.name} {path.name}   # then edit it"
            )
        sys.exit(f"No config at {path}.")
    cfg = json.loads(path.read_text())
    cfg.setdefault("auth_state", str(HERE / "auth.json"))
    cfg.setdefault("artifacts_dir", str(HERE / "artifacts"))
    cfg.setdefault("timeout_ms", 30000)
    return cfg


def artifacts(cfg: dict[str, Any]) -> Path:
    d = Path(cfg["artifacts_dir"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def launch_browser(pw, cfg: dict[str, Any], headless: bool):
    """Launch Chromium, honouring an explicit binary path if one is configured.

    Corporate machines often block `playwright install`, so allow pointing at an
    already-installed Chrome/Chromium via config `chromium_executable`.
    """
    kwargs: dict[str, Any] = {"headless": headless}
    exe = cfg.get("chromium_executable") or os.environ.get("QUDIFY_CHROMIUM")
    if exe:
        if not Path(exe).exists():
            sys.exit(f"chromium_executable does not exist: {exe}")
        kwargs["executable_path"] = exe
    return pw.chromium.launch(**kwargs)


# --------------------------------------------------------------------------- #
# time helpers
# --------------------------------------------------------------------------- #

def parse_date(value: str) -> dt.date:
    """Accept 2026-07-31, 2026/07/31, 'today', 'tomorrow', or a +N day offset."""
    v = value.strip().lower()
    today = dt.date.today()
    if v == "today":
        return today
    if v == "tomorrow":
        return today + dt.timedelta(days=1)
    if re.fullmatch(r"\+\d+", v):
        return today + dt.timedelta(days=int(v[1:]))
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Unrecognised date: {value!r}")


def parse_time(value: str) -> dt.time:
    """Accept 14:00, 2:00 pm, 2pm, 1430."""
    v = value.strip().lower().replace(".", "")
    v = re.sub(r"\s+", " ", v)
    for fmt in ("%H:%M", "%I:%M %p", "%I%p", "%I:%M%p", "%H%M"):
        try:
            return dt.datetime.strptime(v, fmt).time()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Unrecognised time: {value!r}")


def slot_label(start: dt.time) -> str:
    """Render a slot the way the grid labels it: '2:00 pm - 2:30 pm'."""
    base = dt.datetime.combine(dt.date.today(), start)
    end = base + dt.timedelta(minutes=SLOT_MINUTES)

    def fmt(t: dt.datetime) -> str:
        return t.strftime("%I:%M %p").lstrip("0").lower()

    return f"{fmt(base)} - {fmt(end)}"


def parse_duration(value: str) -> int:
    """Minutes, and the grid can only express multiples of its slot size."""
    try:
        minutes = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Duration must be a whole number of minutes: {value!r}")
    if minutes <= 0 or minutes % SLOT_MINUTES:
        raise argparse.ArgumentTypeError(
            f"Duration must be a positive multiple of {SLOT_MINUTES} minutes "
            f"(the grid's slot size); got {minutes}."
        )
    return minutes


def slot_sequence(start: dt.time, duration_min: int) -> list[str]:
    """Every 30-min slot label a meeting of this length occupies."""
    base = dt.datetime.combine(dt.date.today(), start)
    return [
        slot_label((base + dt.timedelta(minutes=i * SLOT_MINUTES)).time())
        for i in range(duration_min // SLOT_MINUTES)
    ]


def normalise(text: str) -> str:
    """Loosen a slot label so '1:00 PM-1:30PM' still matches '1:00 pm - 1:30 pm'."""
    return re.sub(r"\s+", "", (text or "")).lower().replace("–", "-").replace("—", "-")


# --------------------------------------------------------------------------- #
# colour -> slot state
# --------------------------------------------------------------------------- #

def parse_rgb(css: str) -> tuple[int, int, int] | None:
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", css or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def classify(css_colour: str, palette: dict[str, list[int]], tolerance: int) -> str:
    """Nearest-colour match against the legend. Anything far from all of them is free."""
    rgb = parse_rgb(css_colour)
    if rgb is None:
        return "free"
    best, best_dist = "free", None
    for state, ref in palette.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, ref)) ** 0.5
        if best_dist is None or dist < best_dist:
            best, best_dist = state, dist
    if best_dist is not None and best_dist <= tolerance:
        return best
    return "free"


# --------------------------------------------------------------------------- #
# browser
# --------------------------------------------------------------------------- #

class Portal:
    """A logged-in qudify session positioned on the booking grid."""

    def __init__(self, cfg: dict[str, Any], headed: bool = False):
        self.cfg = cfg
        self.sel = cfg["selectors"]
        self.headed = headed
        self._pw = None
        self.browser = None
        self.context = None
        self.page: Page | None = None

    def __enter__(self) -> "Portal":
        state = Path(self.cfg["auth_state"])
        if not state.exists():
            sys.exit(
                f"No saved session at {state}.\n"
                "Run:  python qudify_book.py login"
            )
        self._pw = sync_playwright().start()
        self.browser = launch_browser(self._pw, self.cfg, headless=not self.headed)
        self.context = self.browser.new_context(storage_state=str(state))
        self.context.set_default_timeout(self.cfg["timeout_ms"])
        self.page = self.context.new_page()
        return self

    def __exit__(self, *exc) -> None:
        for closer in (self.context, self.browser):
            try:
                closer and closer.close()
            except Exception:
                pass
        if self._pw:
            self._pw.stop()

    # -- navigation -------------------------------------------------------- #

    def open_grid(self, date: dt.date, office: str | None = None,
                  floor: str | None = None) -> None:
        """Load the booking page and apply office / floor / date filters."""
        page = self.page
        page.goto(self.cfg["booking_url"], wait_until="domcontentloaded")

        office = office or self.cfg.get("office")
        floor = floor or self.cfg.get("floor")

        if office:
            self._select(self.sel["office"], office, "office")
        if floor:
            self._select(self.sel["floor"], floor, "floor")

        self._set_date(date)

        apply_btn = page.locator(self.sel["apply_button"]).first
        if apply_btn.count() and apply_btn.is_enabled():
            apply_btn.click()

        page.wait_for_selector(self.sel["grid"], state="visible")
        page.wait_for_timeout(self.cfg.get("settle_ms", 1200))

    def _select(self, selector: str, value: str, label: str) -> None:
        """Handle both native <select> and custom dropdowns."""
        el = self.page.locator(selector).first
        if not el.count():
            print(f"  ! {label} control not found ({selector}) - skipping", file=sys.stderr)
            return
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            el.select_option(label=value)
            return
        el.click()
        option = self.page.get_by_text(value, exact=True).first
        option.wait_for(state="visible")
        option.click()

    def _set_date(self, date: dt.date) -> None:
        el = self.page.locator(self.sel["date_input"]).first
        if not el.count():
            print("  ! date input not found - skipping", file=sys.stderr)
            return
        fmt = self.cfg.get("date_format", "%Y/%m/%d")
        value = date.strftime(fmt)
        input_type = (el.get_attribute("type") or "").lower()
        if input_type == "date":
            el.fill(date.strftime("%Y-%m-%d"))
        else:
            el.click()
            el.fill("")
            el.type(value, delay=40)
            self.page.keyboard.press("Escape")

    # -- grid reading ------------------------------------------------------ #

    def room_columns(self) -> list[dict[str, Any]]:
        """Room names with their pixel x-ranges, left to right."""
        headers = self.page.locator(self.sel["room_header"])
        cols: list[dict[str, Any]] = []
        for i in range(headers.count()):
            h = headers.nth(i)
            box = h.bounding_box()
            name = (h.inner_text() or "").strip()
            if not box or not name:
                continue
            cols.append({
                "name": name,
                "x0": box["x"],
                "x1": box["x"] + box["width"],
                "cx": box["x"] + box["width"] / 2,
            })
        cols.sort(key=lambda c: c["cx"])
        return cols

    def read_cells(self) -> list[dict[str, Any]]:
        """Every slot cell with its text, position and rendered colour."""
        cells = self.page.locator(self.sel["slot_cell"])
        n = cells.count()
        out: list[dict[str, Any]] = []
        palette = {k: v for k, v in self.cfg["palette"].items()}
        tol = self.cfg.get("colour_tolerance", 60)
        for i in range(n):
            c = cells.nth(i)
            try:
                box = c.bounding_box()
                if not box or box["width"] < 5 or box["height"] < 5:
                    continue
                colour = c.evaluate("e => getComputedStyle(e).backgroundColor")
                text = (c.inner_text() or "").strip()
            except Exception:
                continue
            out.append({
                "index": i,
                "text": text,
                "colour": colour,
                "state": classify(colour, palette, tol),
                "cx": box["x"] + box["width"] / 2,
                "cy": box["y"] + box["height"] / 2,
                "y": box["y"],
            })
        return out

    def cell_for(self, room: dict[str, Any], label: str,
                 cells: list[dict[str, Any]]) -> dict[str, Any] | None:
        """The cell in this room's column carrying this slot label."""
        target = normalise(label)
        matches = [
            c for c in cells
            if room["x0"] - 2 <= c["cx"] <= room["x1"] + 2
            and normalise(c["text"]) == target
        ]
        return matches[0] if matches else None

    def locate(self, cell: dict[str, Any]) -> Locator:
        return self.page.locator(self.sel["slot_cell"]).nth(cell["index"])


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_login(args, cfg) -> int:
    """Log in by hand once; the cookies are reused by every later run."""
    state = Path(cfg["auth_state"])
    with sync_playwright() as pw:
        browser = launch_browser(pw, cfg, headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(cfg.get("login_url") or cfg["booking_url"])
        print("A browser window is open.")
        print("Log in (SSO, password, OTP - whatever your portal uses),")
        print("navigate to the Book Meeting Rooms page, then come back here.")
        input("Press Enter once you can see the booking grid... ")
        context.storage_state(path=str(state))
        browser.close()
    os.chmod(state, 0o600)
    print(f"Session saved to {state} (mode 600). It is gitignored.")
    print("Re-run this command whenever bookings start failing with a login page.")
    return 0


def cmd_capture(args, cfg) -> int:
    """Record the API calls the site makes while you book once by hand."""
    out = artifacts(cfg) / "network_log.json"
    entries: list[dict[str, Any]] = []
    interesting = re.compile(cfg.get("capture_filter", r"api|book|slot|room|meeting"), re.I)

    with Portal(cfg, headed=True) as portal:
        page = portal.page

        def on_request(req):
            if req.method in ("POST", "PUT", "PATCH") or interesting.search(req.url):
                body = None
                try:
                    body = req.post_data
                except Exception:
                    pass
                entries.append({
                    "when": dt.datetime.now().isoformat(timespec="seconds"),
                    "method": req.method,
                    "url": req.url,
                    "body": body,
                })

        page.on("request", on_request)
        page.goto(cfg["booking_url"])
        print("Browser open. Make ONE booking by hand, start to finish.")
        input("Press Enter when the booking is confirmed... ")

    out.write_text(json.dumps(entries, indent=2))
    print(f"Captured {len(entries)} requests -> {out}")
    print("The POST that created the booking is the one worth replaying directly;")
    print("an API-based booker is far faster and more reliable than clicking cells.")
    print("WARNING: this file can contain auth headers/tokens - do not commit it.")
    return 0


def cmd_inspect(args, cfg) -> int:
    """Dump what the script can actually see, so config can be corrected."""
    date = args.date or dt.date.today()
    with Portal(cfg, headed=args.headed) as portal:
        portal.open_grid(date, args.office, args.floor)
        rooms = portal.room_columns()
        cells = portal.read_cells()
        shot = artifacts(cfg) / f"grid-{date:%Y%m%d}.png"
        portal.page.screenshot(path=str(shot), full_page=True)

    print(f"\nDate {date}  |  {len(rooms)} rooms  |  {len(cells)} cells")
    print("\nRooms detected:")
    for i, r in enumerate(rooms):
        print(f"  [{i}] {r['name']:<28} x {r['x0']:.0f}-{r['x1']:.0f}")
    if not rooms:
        print("  (none - fix selectors.room_header in config.json)")

    colours: dict[str, int] = {}
    for c in cells:
        colours[c["colour"]] = colours.get(c["colour"], 0) + 1
    print("\nColours seen (most common first) -> state the script assigned:")
    palette = cfg["palette"]
    tol = cfg.get("colour_tolerance", 60)
    for colour, count in sorted(colours.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {colour:<28} x{count:<4} -> {classify(colour, palette, tol)}")
    print("\nIf a colour is mislabelled, put its rgb into config.json -> palette.")

    if rooms:
        print("\nSample of the first room's column:")
        for c in sorted(
            [c for c in cells if rooms[0]['x0'] - 2 <= c['cx'] <= rooms[0]['x1'] + 2],
            key=lambda c: c["y"],
        )[:14]:
            print(f"  {c['state']:<14} {c['text'][:34]!r}")

    dump = artifacts(cfg) / f"inspect-{date:%Y%m%d}.json"
    dump.write_text(json.dumps({"rooms": rooms, "cells": cells}, indent=2))
    print(f"\nFull dump  -> {dump}")
    print(f"Screenshot -> {shot}")
    return 0


def _pick_room(rooms: list[dict[str, Any]], wanted: str | None,
               index: int | None) -> list[dict[str, Any]]:
    """Rooms to try, in preference order."""
    if index is not None:
        if index >= len(rooms):
            sys.exit(f"--room-index {index} but only {len(rooms)} rooms found.")
        return [rooms[index]]
    if wanted:
        hit = [r for r in rooms if wanted.lower() in r["name"].lower()]
        if not hit:
            names = ", ".join(r["name"] for r in rooms) or "(none detected)"
            sys.exit(f"No room matching {wanted!r}. Rooms: {names}")
        return hit
    return rooms  # --any-room: try them all, left to right


def _attempt(portal: Portal, rooms: list[dict[str, Any]], labels: list[str],
             cfg: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """First room where every needed slot is free. Returns (room, cells to click)."""
    cells = portal.read_cells()
    for room in rooms:
        wanted: list[dict[str, Any]] = []
        for label in labels:
            cell = portal.cell_for(room, label, cells)
            if cell is None or cell["state"] not in ("free", "selected"):
                wanted = []
                break
            wanted.append(cell)
        if wanted:
            return room, wanted
    return None, cells


def _do_book(portal: Portal, args, cfg, labels: list[str]) -> bool:
    """One booking attempt against the currently loaded grid. True if booked."""
    rooms = portal.room_columns()
    if not rooms:
        print("No room columns found - run `inspect` and fix selectors.", file=sys.stderr)
        return False

    candidates = _pick_room(rooms, args.room, args.room_index)
    room, _ = _attempt(portal, candidates, labels, cfg)
    if room is None:
        print(f"  no room has {' + '.join(labels)} free")
        return False

    _, to_click = _attempt(portal, [room], labels, cfg)
    print(f"  {room['name']}: {' + '.join(labels)} free -> selecting")
    for cell in to_click:
        portal.locate(cell).click()
        portal.page.wait_for_timeout(250)

    sel = portal.sel
    if args.title and sel.get("title_input"):
        box = portal.page.locator(sel["title_input"]).first
        if box.count():
            box.fill(args.title)
    if args.attendees and sel.get("attendees_input"):
        box = portal.page.locator(sel["attendees_input"]).first
        if box.count():
            for person in args.attendees.split(","):
                box.type(person.strip(), delay=30)
                portal.page.keyboard.press("Enter")

    shot = artifacts(cfg) / f"before-confirm-{dt.datetime.now():%Y%m%d-%H%M%S}.png"
    portal.page.screenshot(path=str(shot), full_page=True)

    if args.dry_run:
        print(f"  DRY RUN - stopping before confirm. Screenshot: {shot}")
        print("  Check the right cells are green, then re-run without --dry-run.")
        return False

    confirm = portal.page.locator(sel["confirm_button"]).first
    if not confirm.count():
        print(f"  ! confirm button not found ({sel['confirm_button']}).", file=sys.stderr)
        print(f"  ! slots are selected but NOT submitted. See {shot}", file=sys.stderr)
        return False
    confirm.click()
    portal.page.wait_for_timeout(cfg.get("settle_ms", 1200))

    after = artifacts(cfg) / f"after-confirm-{dt.datetime.now():%Y%m%d-%H%M%S}.png"
    portal.page.screenshot(path=str(after), full_page=True)
    print(f"  booked {room['name']} {labels[0].split(' - ')[0]}"
          f"-{labels[-1].split(' - ')[1]}  (screenshot: {after})")
    return True


def cmd_book(args, cfg) -> int:
    labels = slot_sequence(args.start, args.duration)
    print(f"{args.date} | {' + '.join(labels)}")
    with Portal(cfg, headed=args.headed) as portal:
        portal.open_grid(args.date, args.office, args.floor)
        ok = _do_book(portal, args, cfg, labels)
    return 0 if ok else 1


def cmd_watch(args, cfg) -> int:
    """Poll the grid until the slot frees up, then book it."""
    labels = slot_sequence(args.start, args.duration)
    deadline = time.time() + args.max_minutes * 60
    attempt = 0
    print(f"Watching {args.date} {' + '.join(labels)} "
          f"every {args.interval}s for up to {args.max_minutes} min.")
    with Portal(cfg, headed=args.headed) as portal:
        while time.time() < deadline:
            attempt += 1
            print(f"[{dt.datetime.now():%H:%M:%S}] attempt {attempt}")
            try:
                portal.open_grid(args.date, args.office, args.floor)
                if _do_book(portal, args, cfg, labels):
                    return 0
            except PWTimeout:
                print("  page timed out, retrying")
            except Exception as exc:  # keep the watcher alive
                print(f"  error: {exc}")
            time.sleep(args.interval)
    print("Gave up - slot never freed up.")
    return 1


# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    # Shared options, attached to the top level AND to every subcommand, so
    # `book --headed` works as readily as `--headed book`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    common.add_argument("--headed", action="store_true",
                        help="show the browser (useful while tuning)")

    p = argparse.ArgumentParser(
        prog="qudify_book.py",
        description="Automate meeting-room booking on qudify.co.",
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_filters(sp):
        sp.add_argument("--office", help="override config office")
        sp.add_argument("--floor", help="override config floor")

    def add_slot(sp):
        sp.add_argument("--date", type=parse_date, required=True,
                        help="2026-07-31 | today | tomorrow | +7")
        sp.add_argument("--start", type=parse_time, required=True,
                        help="14:00 or '2:00 pm'")
        sp.add_argument("--duration", type=parse_duration, default=60,
                        help=f"minutes, multiple of {SLOT_MINUTES} (default 60)")
        group = sp.add_mutually_exclusive_group()
        group.add_argument("--room", help="room name, partial match")
        group.add_argument("--room-index", type=int, help="column number, 0-based")
        group.add_argument("--any-room", action="store_true",
                           help="take the leftmost room that is free")
        sp.add_argument("--title", help="meeting title, if the portal asks for one")
        sp.add_argument("--attendees", help="comma-separated emails")
        sp.add_argument("--dry-run", action="store_true",
                        help="select the slots and screenshot, but do not confirm")

    sp = sub.add_parser("login", help="save a browser session", parents=[common])
    sp.set_defaults(func=cmd_login)

    sp = sub.add_parser("capture", help="record the site's API calls", parents=[common])
    sp.set_defaults(func=cmd_capture)

    sp = sub.add_parser("inspect", help="dump rooms, slots and colours", parents=[common])
    sp.add_argument("--date", type=parse_date)
    add_filters(sp)
    sp.set_defaults(func=cmd_inspect)

    sp = sub.add_parser("book", help="book a slot", parents=[common])
    add_slot(sp)
    add_filters(sp)
    sp.set_defaults(func=cmd_book)

    sp = sub.add_parser("watch", help="poll until free, then book", parents=[common])
    add_slot(sp)
    add_filters(sp)
    sp.add_argument("--interval", type=int, default=60, help="seconds (default 60)")
    sp.add_argument("--max-minutes", type=int, default=120,
                    help="give up after this long (default 120)")
    sp.set_defaults(func=cmd_watch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "room_index", None) is None and not getattr(args, "room", None) \
            and getattr(args, "any_room", False) is False and args.command in ("book", "watch"):
        sys.exit("Pick a room: --room NAME, --room-index N, or --any-room.")
    cfg = load_config(args.config)
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
