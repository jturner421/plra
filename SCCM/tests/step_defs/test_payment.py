from pytest_bdd import scenario, scenarios, given, when, then, parsers
import pytest
from decimal import Decimal, ROUND_HALF_UP

from SCCM.bin.prisoners import Prisoners
from SCCM.models.case import Case
from SCCM.models.case import Balance

cents = Decimal('0.01')

scenarios('../features/calculate_payment.feature')

@given("I'm a prisoner with an active case", target_fixture='prisoner')
def get_prisoner():
    p = Prisoners('Bob Smith', 1234, Decimal(172.87).quantize(cents, ROUND_HALF_UP))
    p.cases_list.append(Case(case_number='21-cv-12', status='ACTIVE', overpayment=False))
    p.cases_list[0].formatted_case_num = 'DWIW11CV000604'
    return p


@given("I owe $160.65", target_fixture='ccam_balance')
def assign_case(prisoner):
    prisoner.cases_list[0].balance = Balance(amount_assessed=805, amount_collected=644.35, amount_owed=160.65)

    import pandas as pd
    df = pd.read_csv('payments.csv')
    df = df.drop(['debt_typ', 'debt_typ_lnum'], axis=1)
    df.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']
    df = df.sum()
    ccam_account_balance = pd.Series.to_dict(df)
    return ccam_account_balance


@when("I make a payment in the amount of $172.87")
def make_payment_that_results_in_overpayment(prisoner, ccam_balance):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.SingleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should receive a refund of $12.22")
def check_for_overpayment(prisoner):
    assert prisoner.cases_list[0].overpayment is True
    assert prisoner.cases_list[0].balance.amount_owed == 0
    assert prisoner.cases_list[0].balance.amount_collected == 805
    assert prisoner.refund == Decimal(12.22).quantize(cents, ROUND_HALF_UP)


@when("I make a payment in the amount of $126.34")
def make_normal_payment(prisoner, ccam_balance):
    check_number = 57686
    prisoner.amount_paid = Decimal(126.34).quantize(cents, ROUND_HALF_UP)
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.SingleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should have a balance of $34.31")
def check_for_normal_payment(prisoner):
    assert prisoner.cases_list[0].overpayment is False
    assert prisoner.cases_list[0].balance.amount_owed == Decimal(34.31).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[0].balance.amount_collected == Decimal(770.690).quantize(cents, ROUND_HALF_UP)
    assert not hasattr(prisoner, 'refund')
