"""
Performs reconciliation between CCAM and application database

This module compares balances for all prisoners in the application database against JIFMS CCAM, updates case balance, and creates
reconciliation transcation
"""
import os
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import datetime
from datetime import datetime
import warnings

import pandas as pd
import sqlalchemy.orm.exc
from sqlalchemy.exc import SAWarning
from SCCM.bin import ccam_lookup as ccam
import SCCM.services.initiate_global_db_session
from SCCM.services.db_session import DbSession
from SCCM.bin.ccam_lookup import CCAMSettings
from SCCM.config.config_model import PLRASettings
from SCCM.services.database_services import prod_db_backup
from SCCM.models.prisoners import Prisoner
from SCCM.schemas.balance import Balance
from SCCM.models.court_cases import CourtCase
from SCCM.models.case_reconciliation import CaseReconciliation


def get_prisoners_from_db():
    """
    Retrieves all prisoners from database
    :return: list of prisoners
    """
    from sqlalchemy.orm import selectinload
    session = DbSession.factory()
    prisoners = session.query(Prisoner).options(selectinload(Prisoner.cases_list)).all()
    session.close()
    return prisoners


def main():
    config_file = 'SCCM/config/dev.env'
    settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')
    db_session = DbSession.factory()

    # Establish configuration settings
    ccam_settings = CCAMSettings(_env_file='SCCM/ccam.env', _env_file_encoding='utf-8')

    # make backup of SQLite DB
    original = f'{settings.db_base_directory}{settings.db_file}'
    destination = f'{settings.db_backup_directory}/{settings.db_file}_reconciliation_{datetime.now().strftime("%Y%m%d")}'

    # Only make backup of DB the first time
    if not os.path.exists(destination):
        prod_db_backup(original, destination)

    prisoners = get_prisoners_from_db()
    cents = Decimal('0.01')

    for p in prisoners:
        session = DbSession.factory()
        try:
            for case in p.cases_list:
                # retrieve current balance from CCAM
                ccam_balances = ccam.get_ccam_account_information(case.ccam_case_num, settings=ccam_settings,
                                                                  name=p.legal_name)
                ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)
                ccam_case_balances = Balance()
                ccam_case_balances.add_ccam_balances(ccam_summary_balance)

                # balances from DB
                case_db_balances = Balance(amount_assessed=case.amount_assessed,
                                           amount_collected=case.amount_collected,
                                           amount_owed=case.amount_owed)

                assert ccam_case_balances == case_db_balances

        # When they don't match, write updated balance to DB
        except AssertionError:
            print(f'Assertion Error for {p.legal_name} - {case.ccam_case_num}')
            print(f'CCAM: {ccam_case_balances}')
            print(f'DB: {case_db_balances}')
            print('')
            print(f'Updating DB for {p.legal_name} - {case.ccam_case_num}')
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

            session.add_all([case, case_recon])
            session.commit()
        except sqlalchemy.orm.exc.DetachedInstanceError:
            pass


if __name__ == '__main__':
    main()
