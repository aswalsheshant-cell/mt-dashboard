"""Every GitHub Actions pin is a verified Node 24 release (rebuild of old PR #129).

Found 2026-09-26 on main 46738b4: GitHub removed Node 20 from its runners on
2026-09-23 (github.blog changelog 2025-09-19). Every pinned action still targeted
node20 -- runner logs showed "The following actions target Node.js 20 but are
being forced to run on Node.js 24". Three pins in monthly_mt_deck.yml
(checkout f43a0e5, setup-python b64ffca, upload-artifact 4ca96e9) were not
commits of their repos at all ("not our ref"): that workflow has never run and
would have failed at setup on its first schedule. validate.yml only checks that
a pin LOOKS like a 40-hex SHA, which none of this violates.

VERIFIED_PINS was produced by scripts/audit_action_pins.py on 2026-09-26: each
SHA is the tagged commit of that release and its action.yml declares node24.
Target = the lowest major that runs on node24 (fewest breaking changes); every
`with:` input our workflows use exists in the target action.yml.
"""
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w.-]+)*)@([0-9a-f]{40})([^\n]*)")

# action -> (sha, release tag); runs.using == node24 verified upstream 2026-09-26
VERIFIED_PINS = {
    "actions/checkout": ("fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09", "v5.1.0"),
    "actions/setup-python": ("ece7cb06caefa5fff74198d8649806c4678c61a1", "v6.3.0"),
    "actions/setup-node": ("a0853c24544627f65ddf259abe73b1d18a591444", "v5.0.0"),
    "actions/upload-artifact": ("b7c566a772e6b6bfb58ed0dc250532a479d7789f", "v6.0.0"),
    "actions/download-artifact": ("37930b1c2abaa49bbe596cd826c3c89aef350131", "v7.0.0"),
    "actions/github-script": ("ed597411d8f924073f98dfc5c65a23a2325f34cd", "v8.0.0"),
    "github/codeql-action/init": ("2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2", "v4.38.2"),
    "github/codeql-action/analyze": ("2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2", "v4.38.2"),
}


def _pins():
    for f in sorted(glob.glob(str(ROOT / ".github/workflows/*.y*ml"))):
        for n, line in enumerate(Path(f).read_text(encoding="utf-8").splitlines(), 1):
            m = PIN.search(line)
            if m:
                yield Path(f).name, n, m.group(1), m.group(2), m.group(3)


def test_every_pin_is_a_verified_node24_release():
    bad = [(f, n, a, s[:7]) for f, n, a, s, _ in _pins() if VERIFIED_PINS.get(a, (None,))[0] != s]
    assert bad == [], f"pins not in the verified Node 24 set (run scripts/audit_action_pins.py): {bad}"


def test_every_pin_names_its_release_tag():
    bad = [(f, n, a) for f, n, a, s, rest in _pins() if f"# {VERIFIED_PINS[a][1]}" not in rest]
    assert bad == [], bad


def test_workflows_do_use_pinned_actions():
    assert sum(1 for _ in _pins()) >= 50     # guards against the regex silently matching nothing
