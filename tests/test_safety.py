"""Safety guard: the suite must not touch the real database."""

import pytest

from tests.conftest import _REAL_DB_BEFORE, real_db_state
from ticketing.config import DB_ENV_VAR, DEFAULT_DB_PATH, get_db_path


@pytest.mark.req("NFR-003")
def test_env_points_to_tmp_not_real_db():
    assert get_db_path() != DEFAULT_DB_PATH
    import os

    assert os.environ[DB_ENV_VAR] != str(DEFAULT_DB_PATH)


@pytest.mark.req("NFR-003")
def test_real_db_untouched_so_far(db_path, make_ticket):
    make_ticket()
    assert real_db_state() == _REAL_DB_BEFORE
