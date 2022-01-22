from pytest_bdd import scenario, scenarios, given, when, then, parsers
import pytest
from decimal import Decimal, ROUND_HALF_UP

from SCCM.models.prisoner_schema import PrisonerCreate
from SCCM.models.case_schema import CaseCreate
from SCCM.models.case_schema import Balance

cents = Decimal('0.01')


@scenario('../features/calculate_payment_multiple_cases.feature',
          'Multiple Cases, oldest case with balance')
def test_multiple_cases_for_payment():
    """
    Function needed for scenario decorator
    """
    pass


@given("I'm a prisoner with multiple unpaid active cases", target_fixture='prisoner')
def get_prisoner_cases():
    items = {"doc_num": 1234,
             "check_name": 'Bob Smith',
             "amount_paid": Decimal(4.59).quantize(cents, ROUND_HALF_UP)
             }
    p = PrisonerCreate(**items)
    p.cases_list.append(CaseCreate(
        ecf_case_num='16-CV-345',
        comment='ACTIVE')
    )
    p.cases_list.append(CaseCreate(
        ecf_case_num='21-CV-12',
        comment='ACTIVE')
    )

    p.cases_list[0].ccam_case_num = 'DWIW16CV000345'
    p.cases_list[1].ccam_case_num = 'DWIW21CV000012'
    return p


@given("I owe $160.65 in my oldest case")
@given("I owe $350.00 in my newest case")
def assign_case(prisoner):
    prisoner.cases_list[0].balance = Balance(amount_assessed=805, amount_collected=644.35, amount_owed=160.65)
    prisoner.cases_list[1].balance = Balance(amount_assessed=350, amount_collected=0, amount_owed=350.00)


@when("I make a payment in the amount of $4.59")
def make_small_payment_in_oldest_active_case(prisoner):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.MultipleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should have a balance of $156.06 in my oldest case")
@then("I should have a balance of $350.00 in my newest case")
def check_for_balance_in_cases(prisoner):
    assert prisoner.cases_list[0].balance.amount_owed == Decimal(156.06).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].comment == 'ACTIVE'
    assert prisoner.cases_list[0].balance.amount_collected == Decimal(648.94).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[1].balance.amount_owed == Decimal(350.00).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[1].comment == 'ACTIVE'
    assert prisoner.cases_list[1].balance.amount_collected == Decimal(0.00).quantize(cents, ROUND_HALF_UP)
    assert prisoner.refund == 0
