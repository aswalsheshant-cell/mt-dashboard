import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


@pytest.fixture(scope="session")
def data():
    from canonical import facts
    return facts.load_datajs()
