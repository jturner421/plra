"""
Performs reconciliation between CCAM and application database

This module compares balances for all prisoners in the application database against JIFMS CCAM, updates case balance,
and creates reconciliation transaction
"""
import os
from decimal import Decimal
import datetime
from datetime import datetime
from pathlib import Path

import colorama

from SCCM.services.db_session import DbSession
from SCCM.config.config_model import PLRASettings
from SCCM.services.database_services import prod_db_backup
from SCCM.models.prisoners import Prisoner
from SCCM.schemas.balance import Balance
from SCCM.bin import ccam_lookup as ccam
from SCCM.models.case_reconciliation import CaseReconciliation

cents = Decimal('0.01')
env_file = Path.cwd() / 'config' / 'dev.env'
settings = PLRASettings(_env_file=env_file, _env_file_encoding='utf-8')
db_session = DbSession.global_init(db_file=settings.db_base_directory + settings.db_file)
dbsession = DbSession.factory()


def _backup_db():
    # make backup of SQLite DB
    original = f'{settings.db_base_directory}{settings.db_file}'
    destination = (f'{settings.db_backup_directory}/{settings.db_file}_reconciliation_'
                   f'{datetime.now().strftime("%Y%m%d")}')
    # Only make backup of DB the first time
    if not os.path.exists(destination):
        prod_db_backup(original, destination)


def get_prisoners_from_db():
    """
    Retrieves all prisoners from database
    :return: list of prisoners
    """
    from sqlalchemy.orm import selectinload
    prisoners = dbsession.query(Prisoner).options(selectinload(Prisoner.cases_list)).limit(5).all()
    # prisoners = session.query(Prisoner).options(selectinload(Prisoner.cases_list)).all()
    return prisoners


def get_ccam_account_information(case, p):
    ccam_balances = ccam.get_ccam_account_information(case.ccam_case_num, settings=settings,
                                                      name=p.legal_name)
    return ccam_balances


def create_balance_comparison(case, ccam_summary_balance):
    ccam_case_balances = Balance()
    ccam_case_balances.add_ccam_balances(ccam_summary_balance)
    # balances from DB
    case_db_balances = Balance(amount_assessed=case.amount_assessed,
                               amount_collected=case.amount_collected,
                               amount_owed=case.amount_owed)
    return case_db_balances, ccam_case_balances


def reconcile_balances(case, case_db_balances, ccam_case_balances):
    try:
        assert ccam_case_balances == case_db_balances
        print(f'Balances match for {case.prisoner.legal_name} - {case.ccam_case_num}\n')
    except AssertionError:
        print(f'Assertion Error for {case.prisoner.legal_name} - {case.ccam_case_num}')
        print(f'CCAM: {ccam_case_balances}')
        print(f'DB: {case_db_balances}')
        print('')
        print(f'Updating DB for {case.prisoner.legal_name} - {case.ccam_case_num}')
        case.amount_assessed = ccam_case_balances.amount_assessed
        case.amount_collected = ccam_case_balances.amount_collected
        case.amount_owed = ccam_case_balances.amount_owed
        if case.amount_owed == 0:
            case.case_comment = 'PAID'
        case_recon = CaseReconciliation(court_case_id=case.id,
                                        previous_amount_assessed=case_db_balances.amount_assessed,
                                        previous_amount_collected=case_db_balances.amount_collected,
                                        previous_amount_owed=case_db_balances.amount_owed,
                                        updated_amount_assessed=ccam_case_balances.amount_assessed,
                                        updated_amount_collected=ccam_case_balances.amount_collected,
                                        updated_amount_owed=ccam_case_balances.amount_owed)

        dbsession.add_all([case, case_recon])


def main():
    _backup_db()

    prisoners = get_prisoners_from_db()
    cases = [case for p in prisoners for case in p.cases_list]
    for case in cases:
        # retrieve current balance from CCAM
        ccam_balances = get_ccam_account_information(case, case.prisoner)
        ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)
        case_db_balances, ccam_case_balances = create_balance_comparison(case, ccam_summary_balance)

        reconcile_balances(case, case_db_balances, ccam_case_balances)

    dbsession.commit()


if __name__ == '__main__':
    main()
