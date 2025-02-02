import collections
import logging
import ssl
from pathlib import Path
import asyncio

# import backoff
import requests
from requests import Session
from http.client import HTTPConnection
import json
import aiohttp

import pandas as pd
from pydantic import BaseSettings, Field, SecretStr
from colorama import Fore

from SCCM.models.court_cases import CourtCase

# from SCCM.bin.retry import retry

log = logging.getLogger('urllib3')
log.setLevel(logging.WARN)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.WARN)
log.addHandler(ch)


class CCAMSettings(BaseSettings):
    """
    Pydantic model for managing CCAM API settings
    ccam.env stored in project root
    """
    ccam_username: str = Field(..., env='CCAM_USERNAME')
    ccam_password: SecretStr = Field(..., env='CCAM_PASSWORD')
    base_url: str = Field(..., env='BASE_URL')
    cert_file: str = Field(..., env='CERT_FILE')

    class Config:
        case_sensitive = False
        env_file = Path.cwd() / 'config' / 'dev.env'
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
        self.session.close()


def get_ccam_account_information(cases, **kwargs):
    """
    Retrieves JIFMS CCAM information for case via API call

    :param cases: case object

    :return: dictionary of account balances for requested case
    """
    if kwargs['settings']:
        settings = kwargs['settings']
    with CCAMSession(settings.ccam_username, settings.ccam_password.get_secret_value(), settings.ccam_url,
                     settings.cert_file) as session:
        print(Fore.YELLOW + f'Getting case balances from CCAM for {kwargs["name"]}')
        data = {"caseNumberList": cases}
        headers = {
            'Content-Type': 'application/json'
        }

        response = session.get(
            settings.ccam_url,
            headers=headers,
            params=data).json()

        ccam_data = response["data"]

        # API pagination set at 20. This snippet retrieves the rest of the records.  Note: API does not return next page
        # url so we need to rely on total pages embedded in the metadata
        # todo: catch too many requests error
        if response['meta']['pageInfo']['totalPages'] > 1:
            for page in range(2, response['meta']['pageInfo']['totalPages'] + 1):
                data = {"caseNumberList": cases, "page": page}
                response = session.get(
                    settings.ccam_url,
                    headers=headers,
                    params=data).json()
                ccam_data.extend(response["data"])

    return ccam_data


async def async_get_ccam_account_information(session, ccam_case_num: str, **kwargs) -> list[dict]:
    """
    Retrieves JIFMS CCAM information for case via API call

    :param ccam_case_num: ccam case number

    :return: list of dictionaries of account balances for requested case
    """
    data = {"caseNumberList": ccam_case_num}
    # print(Fore.CYAN + f'Getting case balances from CCAM for {kwargs["name"]} - {kwargs["ecf_case_num"]}')
    ccam_data = await session.get_CCAM_balances_async(data, ccam_case_num)
    return ccam_data


def sum_account_balances(payments: list[dict]) -> tuple[pd.DataFrame, str]:
    """
    Totals CCAM payment lines and updates prison object with payment information as a Python List

    :param payments: List of individual payment lines for a case
    :return: case balances and party code
    """

    # create a pandas dataframe
    df = pd.DataFrame(payments)
    df = df.fillna(0)

    # get party code
    party_code = df.drop_duplicates('prty_cd')

    # get account sums grouped by case number
    balances = df.groupby(df.case_num).sum(['prnc_owed', 'prnc_clld', 'totl_ostg'])
    balances = balances.drop(['debt_typ_lnum'], axis=1)
    balances.columns = ['Total Owed', 'Total Collected', 'Total Outstanding']

    # retrieve account codes and add to balances
    accounts = df.drop_duplicates('case_num', keep='last')
    accounts.reset_index(drop=True, inplace=True)
    accounts.set_index(['case_num'], inplace=True)
    balances = balances.join(accounts.acct_cd, how='left')
    return balances
