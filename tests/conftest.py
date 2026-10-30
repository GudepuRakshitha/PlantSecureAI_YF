"""Shared pytest fixtures.

The suite runs against the committed CSV dataset.  Expensive population
preparation is session-scoped so individual tests stay fast.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import data_access  # noqa: E402


@pytest.fixture(scope="session")
def baseline() -> dict[str, object]:
    return data_access.prepare_population("baseline")


@pytest.fixture(scope="session")
def scenario() -> dict[str, object]:
    return data_access.prepare_population("scenario")


@pytest.fixture(scope="session")
def baseline_frames() -> dict[str, object]:
    return data_access.load_population("baseline")
