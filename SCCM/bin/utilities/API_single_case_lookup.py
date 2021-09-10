"""
Command line JIFMS case lookup. Uses API to retrieve case information and prints to screen.
"""
from pathlib import Path

import keyring
import requests
import string
from SCCM.bin.ccam_lookup import get_ccam_account_information
from SCCM.bin.convert_to_excel import format_case_num
from SCCM.config import config


def main():
    p = Path.cwd()
    config_file = p.parent.parent / 'config' / 'config.ini'
    configuration = config.initialize_config(str(config_file))
    prod_vars = config.get_prod_vars(configuration, 'PROD')
    ccam_username = prod_vars['CCAM_USERNAME']
    base_url = prod_vars['CCAM_API']
    ccam_password = keyring.get_password("WIWCCA", ccam_username)
    session = requests.Session()
    session.auth = (ccam_username, ccam_password)
    cert_path = prod_vars['CLIENT_CERT_PATH']
    session.verify = cert_path

    case_number = input('Enter Case Number (yy-cv-number-xxx(if multi-defendant case):  ')
    formatted_case_num = format_case_num(str.upper((case_number)))

    balance = get_ccam_account_information(formatted_case_num, session, base_url)
    if len(balance['data']) >> 0:
        for k, v in enumerate(balance['data']):
            print(f"Fund {v['debt_typ']}, Case #: {v['case_num']}, Account Code: {v['prty_cd']}, "
                  f"Party Num: {v['prty_num']},  Name: {v['prty_nm']}, "
                  f" Amount Owed: {v['prnc_owed_am']}, Amount Collected: {v['prnc_clld_am']}, "
                  f"Amount Outstanding {v['totl_ostg_am']}")
    else:
        print("No records found")

if __name__ == '__main__':
    main()