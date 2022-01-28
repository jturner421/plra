from pytest_bdd import scenario, scenarios, given, when, then, parsers
import pytest
from decimal import Decimal, ROUND_HALF_UP

from SCCM.schemas.prisoner_schema import PrisonerCreate
from SCCM.schemas.case_schema import CaseCreate
from SCCM.schemas.case_schema import Balance

cents = Decimal('0.01')


@scenario('../features/calculate_payment.feature', 'Single Case is paid off')
@scenario('../features/calculate_payment.feature', 'Single Case with balance')
@scenario("../features/calculate_payment.feature", 'No Case')
def test_single_payment():
    pass


@given("I'm a prisoner with an active case", target_fixture='prisoner')
def get_prisoner():
    items = {"doc_num": 1234,
             "legal_name": 'Wayne Hart',
             "amount_paid": Decimal(172.87).quantize(cents, ROUND_HALF_UP)
             }
    p = PrisonerCreate(**items)
    p.cases_list.append(CaseCreate(
        ecf_case_num='21-CV-12',
        case_comment='ACTIVE')
    )
    p.cases_list[0].ccam_case_num = 'DWIW21CV000012'
    return p


@given("I'm a prisoner with no active cases", target_fixture='prisoner_nocase')
def get_prisoner_with_no_case():
    items = {"doc_num": 1234,
             "legal_name": 'Wayne Hart',
             "amount_paid": Decimal(50.00).quantize(cents, ROUND_HALF_UP)
             }
    p = PrisonerCreate(**items)
    return p


@given("I owe $160.65")
def assign_case(prisoner):
    prisoner.cases_list[0].balance = Balance(amount_assessed=805, amount_collected=644.35, amount_owed=160.65)


@when("I make a payment in the amount of $172.87")
def make_payment_that_results_in_overpayment(prisoner):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.SingleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should receive a refund of $12.22")
def check_for_overpayment(prisoner):
    assert prisoner.cases_list[0].balance.amount_owed == 0
    assert prisoner.cases_list[0].balance.amount_collected == 805
    assert prisoner.refund == Decimal(12.22).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].transaction.amount_paid == Decimal(160.65).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].transaction.check_number == 57686


@when("I make a payment in the amount of $126.34")
def make_normal_payment(prisoner):
    check_number = 57686
    prisoner.amount_paid = Decimal(126.34).quantize(cents, ROUND_HALF_UP)
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.SingleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should have a balance of $34.31")
def check_for_normal_payment(prisoner):
    assert prisoner.cases_list[0].balance.amount_owed == Decimal(34.31).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].balance.amount_collected == Decimal(770.690).quantize(cents, ROUND_HALF_UP)
    assert prisoner.refund is None
    assert prisoner.cases_list[0].transaction.amount_paid == Decimal(126.34).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].transaction.check_number == 57686


@when("I make a payment in the amount of $50.00")
def make_payment_with_no_active_cases(prisoner_nocase):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.OverPaymentProcess())
    context.process_payment(prisoner_nocase, check_number)


@then("I should receive a refund of $50.00")
def process_overpayment(prisoner_nocase):
    assert prisoner_nocase.overpayment
    assert prisoner_nocase.overpayment['transaction amount'] == -50.00
    assert prisoner_nocase.overpayment['ccam_case_num'] == 'No Active Cases'
    assert prisoner_nocase.refund == 50.00
