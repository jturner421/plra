"""
Command line database case lookup. Retrieves case information and prints to screen.
"""

from pathlib import Path
import warnings
from sqlalchemy.exc import SAWarning
import sqlalchemy as sa
from decimal import *

from SCCM.config import config
from SCCM.data.court_cases import CourtCase
from SCCM.data.db_session import DbSession


def main():
    p = Path.cwd()
    config_file = p.parent.parent / 'config' / 'config.ini'
    configuration = config.initialize_config(str(config_file))
    prod_vars = config.get_prod_vars(configuration, 'PROD')
    prod_db_path = prod_vars['NETWORK_DB_BASE_DIR']
    db_file_name = prod_vars['DATABASE_SQLite']
    db_file = f'{prod_db_path}{db_file_name}'
    db_session = DbSession.global_init(db_file)

    # Suppress SQLAlchemy warning about Decimal storage.
    warnings.filterwarnings('ignore', r".*support Decimal objects natively", SAWarning, r'^sqlalchemy\.sql\.sqltypes$')

    case_number = input('Enter Case Number (yy-cv-number-xxx(if multi-defendant case):  ')

    s = db_session
    case_balance = s.query(CourtCase, CaseBalance).filter(CourtCase.ecf_case_num == case_number.upper()) \
        .filter(CourtCase.id == CaseBalance.court_case_id).first()

    cents = Decimal('0.01')

    print(f'The balance for case number {case_balance.CourtCase.ecf_case_num} '
          f'for {case_balance.CourtCase.prisoner.judgment_name} is: \n \n'
          f'Amount Assessed: {Decimal(case_balance.CaseBalance.amount_assessed).quantize(cents, ROUND_HALF_UP)}\n'
          f'Amount Collected: {Decimal(case_balance.CaseBalance.amount_collected).quantize(cents, ROUND_HALF_UP)}\n'
          f'Amount Owed: {Decimal(case_balance.CaseBalance.amount_owed).quantize(cents, ROUND_HALF_UP)}\n ')
    if case_balance.CaseBalance.case.case_comment == 'PAID':
        print(f'This case is paid in full \n')
    else:
        print(f'This case is active \n')

    transactions = case_balance.CourtCase.case_transactions
    print(f'The last several transactions are:')
    for index, value in enumerate(transactions):
        print(f'Date paid: {value.created_date} '
              f'Check Number: {value.check_number} '
              f'Amount paid: {Decimal(value.amount_paid).quantize(cents, ROUND_HALF_UP)}')


if __name__ == '__main__':
    main()
