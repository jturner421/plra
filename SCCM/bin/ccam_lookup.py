import collections
import logging
import requests
from requests import Session
from http.client import HTTPConnection
import json

import pandas as pd
from pydantic import BaseSettings, Field, SecretStr

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
def get_ccam_account_information(cases, **kwargs):
    """
    Retrieves JIFMS CCAM information for case via API call
    :param cases: case object

    :return: dictionary of account balances for requested case
    """
    if kwargs['settings']:
        settings = kwargs['settings']
    with CCAMSession(settings.ccam_username, settings.ccam_password.get_secret_value(), settings.base_url,
                     settings.cert_file) as session:
        print(f'Getting case balances from CCAM for {kwargs["name"]}\n')
        data = {"caseNumberList": cases}
        headers = {
            'Content-Type': 'application/json'
        }

        response = session.get(
            settings.base_url,
            headers=headers,
            params=data).json()

        ccam_data = response["data"]
        for page in range(2, response['meta']['pageInfo']['totalPages'] + 1):
            data = {"caseNumberList": cases, "page": page}
            response = session.get(
                settings.base_url,
                headers=headers,
                params=data).json()
            ccam_data.extend(response["data"])

    return ccam_data


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


def sum_account_balances(payments):
    """
    Totals CCAM payment lines and updates prison object with payment information as a Python List
    :param payments: List of individual payment lines for a case
    :return: None
    """

    # create a pandas dataframe
    df = pd.DataFrame(payments)
    df = df.fillna(0)

    # get party code
    party_code = df.drop_duplicates('prty_cd')

    # get account sums grouped by case number
    balances = df.groupby(df.case_num).sum()
    balances = balances.drop(['debt_typ_lnum'], axis=1)
    balances.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']

    # retrieve account codes and add to balances
    accounts = df.drop_duplicates('case_num', keep='last')
    accounts.reset_index(drop=True, inplace=True)
    accounts.set_index(['case_num'], inplace=True)
    balances = balances.join(accounts.acct_cd, how='left')

    # ccam_account_balance = pd.Series.to_dict(balances)
    return balances, party_code.prty_cd.values[0]


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
