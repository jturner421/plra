from pytest_bdd import scenario, scenarios, given, when, then, parsers
import pytest
from decimal import Decimal, ROUND_HALF_UP

from SCCM.bin.prisoners import Prisoners
from SCCM.models.case import Case
from SCCM.models.case import Balance

cents = Decimal('0.01')


# scenarios('../features/calculate_overpayment.feature')


@scenario('../features/calculate_overpayment.feature', 'Multiple Cases, oldest case paid, newest case with balance')
def test_overpayment():
    pass


@given("I'm a prisoner with multiple active cases", target_fixture='prisoner')
def get_prisoner():
    p = Prisoners('Bob Smith', 1234, Decimal(178.32).quantize(cents, ROUND_HALF_UP))
    p.cases_list.append(Case(case_number='16-cv-345', status='ACTIVE', overpayment=False))
    p.cases_list.append(Case(case_number='21-cv-12', status='ACTIVE', overpayment=False))
    p.cases_list[0].formatted_case_num = 'DWIW16CV000345'
    p.cases_list[1].formatted_case_num = 'DWIW21CV000012'
    return p


@given("I owe $160.65 in my oldest case", target_fixture='ccam_balance')
@given("I owe $350.00 in my newest case", target_fixture='ccam_balance')
def assign_case(prisoner):
    prisoner.cases_list[0].balance = Balance(amount_assessed=805, amount_collected=644.35, amount_owed=160.65)
    prisoner.cases_list[1].balance = Balance(amount_assessed=350, amount_collected=0, amount_owed=350.00)

    # simulat CCAM API call without a mock
    import pandas as pd
    df = pd.read_csv('payments.csv')
    df = df.drop(['debt_typ', 'debt_typ_lnum'], axis=1)
    df.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']
    df = df.sum()
    ccam_account_balance = pd.Series.to_dict(df)
    return ccam_account_balance


@when("I make a payment in the amount of $178.32")
def make_payment_that_results_in_overpayment(prisoner, ccam_balance):
    check_number = 57686
    import SCCM.bin.payment_strategy as payment
    context = payment.Context(payment.MultipleCasePaymentProcess())
    context.process_payment(prisoner, check_number)


@then("I should have a balance of $0.00 in my oldest case")
@then("I should have a balance of $332.23 in my newest case")
def check_for_overpayment(prisoner):
    assert prisoner.cases_list[0].balance.amount_owed == 0
    assert prisoner.cases_list[0].status == 'PAID'
    assert prisoner.cases_list[0].balance.amount_collected == 805
    assert prisoner.cases_list[1].overpayment is False
    assert prisoner.cases_list[1].balance.amount_owed == Decimal(332.33).quantize(cents, ROUND_HALF_UP)
    assert prisoner.cases_list[1].status == 'ACTIVE'
    assert prisoner.cases_list[1].balance.amount_collected == Decimal(17.67).quantize(cents, ROUND_HALF_UP)

