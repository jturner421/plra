"""
Command line JIFMS case lookup. Uses API to retrieve case information and prints to screen.
"""
import pandas as pd

from SCCM.bin.ccam_lookup import get_ccam_account_information, CCAMSettings, sum_account_balances
from SCCM.bin.convert_to_excel import format_case_num


def main():
    settings = CCAMSettings(_env_file='../../ccam.env', _env_file_encoding='utf-8')
    case_number = input('Enter CaseBase Number (yy-cv-number-xxx(if multi-defendant case):  ')
    formatted_case_num = format_case_num(str.upper(case_number))
    ccam_balances = get_ccam_account_information(formatted_case_num, settings=settings, name=case_number)
    ccam_summary_balance, party_code = sum_account_balances(ccam_balances)
    prisoner_name = {c['prty_nm'] for c in ccam_balances}
    balance = ccam_summary_balance.to_dict()
    print(f'\n \nCCAM Balance for case {str.upper(case_number)} for {prisoner_name} is \n'
          f"Principal Owed: {balance['Total Owed']}\n"
          f"Total Collected: {balance['Total Collected']}\n"
          f"Total Outstanding: {balance['Total Outstanding']}")


if __name__ == '__main__':
    main()
