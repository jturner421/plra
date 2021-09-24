import collections
import logging
import requests
from requests import Session
from http.client import HTTPConnection

import pandas as pd
from pydantic import BaseSettings, Field, SecretStr

from SCCM.data.case_balance import CaseBalance
from SCCM.data.court_cases import CourtCase
from SCCM.bin.retry import retry

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1


class CCAMSettings(BaseSettings):
    """
    Pydantic model for managing CCAM API settings
    """
    ccam_username: str = Field(..., env='CCAM_USERNAME')
    ccam_password: SecretStr = Field(..., env='CCAM_PASSWORD')
    base_url: str = Field(..., env='BASE_URL')
    cert_file: str = Field(..., env='CERT_FILE')

    class Config:
        case_sensitive = False
        env_file = '../ccam.env'
        env_file_encoding = 'utf-8'


settings = CCAMSettings()


class CCAMSession:
    """
    Manage Requests sessions with context manager

    """

    def __init__(self, username: str, password: str, url: str, cert: str):
        self.username = username
        self.password = password
        self.url = url
        self.cert = cert

    def __enter__(self) -> Session:
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = self.cert
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        # if int(response.headers['Keep-Alive'].split(',')[1].split('=')[-1]) <= 20:
        #     session.close()
        self.session.close()


@retry(Exception, tries=4)
def get_ccam_account_information(case):
    """
    Retrieves JIFMS CCAM information for case via API call
    :param case: case object

    :return: dictionary of account balances for requested case
    """
    with CCAMSession(settings.ccam_username, settings.ccam_password.get_secret_value(), settings.base_url,
                     settings.cert_file) as session:
        print(f'Getting case balances from JIFMS for {case.case_number}\n')
        response = session.get(
            settings.base_url,
            params={'caseNumberList': case.formatted_case_num},

        )
    return response.json()


def insert_ccam_account_balances(p, db_session):
    """
    Inserts JIFMS CCAM balances for current payee and identified case
    :param p: Person object
    :param db_session: SQLAlchemy session
    """
    # get DB session
    s = db_session
    result = s.query(CourtCase).filter(CourtCase.ecf_case_num == p.orig_case_number).first()
    balances = [p.ccam_balance["Total Owed"], p.ccam_balance["Total Collected"], p.ccam_balance["Total Outstanding"]]
    result.case_balance.append(CaseBalance(court_case_id=result.id, amount_assessed=balances[0],
                                           amount_collected=balances[1], amount_owed=balances[2]))
    s.commit()
    s.close()


def sum_account_balances(payments, case):
    """
    Totals CCAM payment lines and updates prison object with payment information as a Python List
    :param payments: List of individual payment lines for a case
    :return: None
    """

    # parse payments
    payment_lines = []
    for i in range(len(payments['data'])):
        payment_lines.append(payments['data'][i])
    df = pd.DataFrame(payment_lines)
    party_code = df.iloc[0]['acct_cd']

    df = df.drop(['case_num', 'case_titl', 'prty_num', 'prty_nm', 'scty_org', 'debt_typ', 'debt_typ_lnum', 'acct_cd',
                  'prty_cd', 'last_updated'], axis=1)
    df.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']
    df = df.sum()
    ccam_account_balance = pd.Series.to_dict(df)
    return ccam_account_balance, party_code


OverPaymentInfo = collections.namedtuple('OverPaymentInfo', 'exists, amount_overpaid')


def check_for_overpayment(prisoner):
    """
    Calculates overpayment for payment if exists

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
