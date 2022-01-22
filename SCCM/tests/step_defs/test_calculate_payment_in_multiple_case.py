from pytest_bdd import scenario, scenarios, given, when, then, parsers
import pytest
from decimal import Decimal, ROUND_HALF_UP

from SCCM.models.prisoner_schema import PrisonerCreate
from SCCM.models.case_schema import CaseCreate
from SCCM.models.case_schema import Balance
cents = Decimal('0.01')


@scenario('../features/calculate_payment_multiple_cases.feature',
          'Multiple Cases, oldest case paid, newest case with balance')
def test_multiple_cases_with_overpayment():
    """
    Function needed for scenario decorator
    """
    pass


@given("I'm a prisoner with multiple active cases", target_fixture='prisoner')
def get_prisoner():
    items = {"doc_num": 1234,
             "check_name": 'Bob Smith',
             "amount_paid": Decimal(178.32).quantize(cents, ROUND_HALF_UP)
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


@when("I make a payment in the amount of $178.32")
def make_payment_that_results_in_overpayment(prisoner):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.MultipleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should have a balance of $0.00 in my oldest case")
@then("I should have a balance of $332.23 in my newest case")
def check_for_balance_in_newest_case(prisoner):
    assert prisoner.cases_list[0].balance.amount_owed == 0
    assert prisoner.cases_list[0].comment == 'PAID'
    assert prisoner.cases_list[0].balance.amount_collected == 805
    assert prisoner.cases_list[1].balance.amount_owed == Decimal(332.33).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[1].comment == 'ACTIVE'
    assert prisoner.cases_list[1].balance.amount_collected == Decimal(17.67).quantize(cents, ROUND_HALF_UP)
    assert prisoner.refund == 0.00
