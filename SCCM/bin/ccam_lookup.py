import collections
from decimal import *

import pandas as pd

from SCCM.data.case_balance import CaseBalance
from SCCM.data.court_cases import CourtCase


def get_ccam_account_information(case_num, session, base_url):
    """
    Retrieves JIFMS CCAM information for case via API call
    :param case_num: formatted payee case number e.g. DWIW312CV000234-001
    :param session: Requests session object
    :param base_url: base API url
    :return: dictionary of account balances for identified case
    """
    try:
        case_string_split = str.split(case_num, '-')
        case = f'{str.upper(case_string_split[0])}-{case_string_split[1]}'
        print(f'Getting case balances from JIFMS for {case}\n')
        response = session.get(
            base_url,
            params={'caseNumberList': case},
        )
        return response.json()
    except TypeError as e:
        print(' An error occurred ')


def insert_ccam_account_balances(p, db_session):
    """
    Inserts JIFMS CCAM balances for current payee and identified case
    :param p: Person object
    :param db_session: SQLAlchemy session
    """
    # get DB session
    s = db_session
    result = s.query(CourtCase).filter(CourtCase.case_num == p.orig_case_number).first()
    balances = [p.ccam_balance["Total Owed"], p.ccam_balance["Total Collected"], p.ccam_balance["Total Outstanding"]]
    result.case_balance.append(CaseBalance(court_case_id=result.id, amount_assessed=balances[0],
                                           amount_collected=balances[1], amount_owed=balances[2]))
    s.commit()
    s.close()


def sum_account_balances(payments, p):
    """
    Totals CCAM payment lines and updates prison object with payment information as a Python List
    :param payments: List of individual payment lines for a case
    :param p: Prison object
    :return: None
    """

    # parse payments
    payment_lines = []
    for i in range(len(payments['data'])):
        # payment_lines[i] = payments['data'][i]
        payment_lines.append(payments['data'][i])
    df = pd.DataFrame(payment_lines)
    p.pty_cd = df.iloc[0]['acct_cd']
    p.acct_cd = df.iloc[0]['prty_cd']

    df = df.drop(['case_num', 'case_titl', 'prty_num', 'prty_nm', 'scty_org', 'debt_typ', 'debt_typ_lnum', 'acct_cd',
                  'prty_cd', 'last_updated'], axis=1)
    df.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']
    df = df.sum()
    ccam_account_balance = pd.Series.to_dict(df)
    p.ccam_balance = ccam_account_balance
    return p


OverPaymentInfo = collections.namedtuple('OverPaymentInfo', 'exists, amount_overpaid')


def check_for_overpayment(prisoner):
    """
    Calculates overpayment for payment if exists
    :param amount: Amount paid by payee on state check
    :param balance: CCAM account balance
    :return: Exists > Bool, amount overpaid
    """
    try:
        if prisoner.amount <= prisoner.current_case.case_balance[0].amount_owed:
            overpayment = False
            check_overpaid = OverPaymentInfo(exists=overpayment, amount_overpaid=0.00)
            prisoner.overpayment = check_overpaid
            return prisoner
        else:
            overpayment = True
            amount_overpaid = prisoner.current_case.case_balance[0].amount_owed - prisoner.amount
            check_overpaid = OverPaymentInfo(exists=overpayment, amount_overpaid=amount_overpaid)
            prisoner.overpayment = check_overpaid
            return prisoner
    except AttributeError:
        overpayment = True
        amount_overpaid = prisoner.amount
        check_overpaid = OverPaymentInfo(exists=overpayment, amount_overpaid=amount_overpaid)
        prisoner.overpayment = check_overpaid
        return prisoner
