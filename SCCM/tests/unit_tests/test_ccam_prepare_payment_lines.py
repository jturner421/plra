import pytest
import SCCM.services.payment_services as ps
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP

cents = Decimal('0.01')


def test_fixture_working(setup_prisoner):
    # result = ps.prepare_ccam_upload_transactions([setup_prisoner_refund])
    assert len(setup_prisoner.cases_list) == 3
    assert setup_prisoner.cases_list[0].balance.amount_collected == Decimal(91.28).quantize(cents, ROUND_HALF_UP)


def test_ccam_payment_lines_no_refund(setup_prisoner):
    result = ps.prepare_ccam_upload_transactions([setup_prisoner])
    assert len(result)==2