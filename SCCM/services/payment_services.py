from SCCM.schemas.prisoner_schema import PrisonerCreate
from decimal import Decimal, ROUND_HALF_UP
from pandas import DataFrame
from SCCM.schemas.case_schema import CaseCreate
from SCCM.schemas.transaction_schema import TransactionCreate

cents = Decimal('0.01')


def prepare_ccam_upload_transactions(prisoner_list):
    # Save Excel file for upload to JIFMS
    payments = []
    for p in prisoner_list:
        if p.overpayment:
            for case in p.cases_list:
                if case.transaction:
                    payments.append({'prisoner': p, 'case': case})
            payments.append({'prisoner': p})
        else:
            for case in p.cases_list:
                try:
                    if case.transaction:
                        payments.append({'prisoner': p, 'case': case})
                except AttributeError as e:
                    print(f'ERROR: {e}')
                    print(f'ERROR: {p.legal_name} - {case} has no transaction')
    return payments


def prepare_overpayment_multiple(p: PrisonerCreate, case: CaseCreate, check_number: int) -> PrisonerCreate:
    case.case_comment = 'PAID'
    overpayment = case.balance.mark_paid()
    case.transaction = TransactionCreate(
        check_number=check_number, amount_paid=p.amount_paid - Decimal(overpayment).quantize(cents, ROUND_HALF_UP))
    p.refund = overpayment
    p.overpayment = {'overpayment': True,
                     'ccam_case_num': case.ccam_case_num,
                     'assessed': case.balance.amount_assessed,
                     'collected': case.balance.amount_collected,
                     'outstanding': case.balance.amount_owed,
                     'transaction amount': -p.refund
                     }
    p.amount_paid = p.refund
    return p, case


def prepare_overpayment_single(p: PrisonerCreate, case: CaseCreate, check_number: int) -> PrisonerCreate:
    case.case_comment = 'PAID'
    overpayment = case.balance.mark_paid()
    p.refund = overpayment
    p.overpayment = {'overpayment': True,
                     'ccam_case_num': case.ccam_case_num,
                     'assessed': case.balance.amount_assessed,
                     'collected': case.balance.amount_collected,
                     'outstanding': case.balance.amount_owed,
                     'transaction amount': -p.refund
                     }
    case.transaction = TransactionCreate(
        check_number=check_number, amount_paid=(p.amount_paid - p.refund).quantize(cents, ROUND_HALF_UP))
    p.amount_paid = p.refund
    return p, case


def prepare_payment(p: PrisonerCreate, case: CaseCreate, check_number: int) -> CaseCreate:
    case.transaction = TransactionCreate(
        check_number=check_number, amount_paid=p.amount_paid.quantize(cents, ROUND_HALF_UP))
    return p, case


def check_sum(check_amount: Decimal, total_by_name_sum: Decimal) -> None:
    """
    Compares aggregate total against individual payments to insure they match

    :param check_amount: Total check amount
    :param total_by_name_sum: Aggregate sum of prisoner payments
    :return:
    """
    try:
        assert total_by_name_sum == check_amount
        print(
            f'Check amount of {check_amount:,.2f} matches the sum of the converted file - {total_by_name_sum:,.2f}')
    except AssertionError:
        print(
            f"ERROR: The sum of the file header:{check_amount:,.2f} does not match the sum:{total_by_name_sum:,.2f}"
            f" of the converted file.\n")


def prepare_deposit_number(check_date) -> str:
    """
    Prepare CCAM deposit number format

    :param check_date:
    :return: deposit number
    """
    check_date_split = str.split(check_date, '/')
    deposit_num = f"PL{check_date_split[0]}{check_date_split[1]}{check_date_split[2][2:]}"
    return deposit_num


def get_check_sum(state_check_data: DataFrame) -> Decimal:
    """
    Returns aggregate sums of prisoner payments

    :param state_check_data: pandas dataframe of prisoners with amount paid
    :return: total of all prisoners
    """
    total_by_name_sum = state_check_data['Amount'].sum()
    total_by_name_sum = Decimal(total_by_name_sum).quantize(cents, ROUND_HALF_UP)
    return cents, total_by_name_sum
