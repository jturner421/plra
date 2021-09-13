import pytest

from SCCM.data.prisoners import PrisonerFactory


def test_start(populate_test_db):
    p = PrisonerFactory()
    assert 1 == 1
