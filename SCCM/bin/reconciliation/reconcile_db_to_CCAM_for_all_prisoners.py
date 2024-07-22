"""
Performs reconciliation between CCAM and application database

This module compares balances for all prisoners in the application database against JIFMS CCAM, updates case balance,
and creates reconciliation transaction
"""
import os
from decimal import Decimal, ROUND_HALF_UP
import datetime
from datetime import datetime
from pathlib import Path
import asyncio

from colorama import Fore
from pandas import DataFrame, Series
from SCCM.models.court_cases import CourtCase
from SCCM.services.db_session import DbSession
from SCCM.config.config_model import PLRASettings
from SCCM.services.database_services import prod_db_backup
from SCCM.models.prisoners import Prisoner
from SCCM.schemas.balance import Balance, BalanceRecon
from SCCM.bin import ccam_lookup as ccam
from SCCM.util import async_timed
from bin.ccam_lookup import async_get_ccam_account_information, sum_account_balances
from services.api_services import AsyncHttpClient
from SCCM.models.case_reconciliation import CaseReconciliation

# Globals
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
    # Only make backup of DB the first time that day
    if not os.path.exists(destination):
        prod_db_backup(original, destination)


def get_prisoners_from_db() -> list[Prisoner]:
    """
    Retrieves all prisoners from database
    :return: list of prisoners
    """
    from sqlalchemy.orm import selectinload
    prisoners = dbsession.query(Prisoner).options(selectinload(Prisoner.cases_list)).all()
    return prisoners


def create_balance_comparison(case: str, ccam_summary_balance: DataFrame) -> tuple[Balance, Balance]:
    """
    Creates balance objects for CCAM and database values.
    :param case: case object
    :param ccam_summary_balance: Dataframe of CCAM balances
    :return:
    """
    ccam_case_balances = BalanceRecon()
    ccam_case_balances.add_ccam_balances(ccam_summary_balance)
    return ccam_case_balances


def reconcile_balances(case: CourtCase, ccam_case_balances: Series) -> None:
    """
    Compares CCAM and database balances. If they do not match, the database is updated and a reconciliation transaction
    :param case: case object
    :param ccam_case_balances: CCAM balances
    :return: None
    """
    try:
        assert case.amount_owed.quantize(cents, ROUND_HALF_UP) == Decimal(
            ccam_case_balances.loc['Total Outstanding'].item()).quantize(cents, ROUND_HALF_UP)
        print(Fore.BLUE + f'Balances match for {case.prisoner.legal_name} - {case.ecf_case_num}\n')
    except AssertionError:
        print(Fore.RED + f'Balances do not match {case.prisoner.legal_name} - {case.ecf_case_num}')
        print(f'Updating Database for {case.prisoner.legal_name} - {case.ecf_case_num}')
        case_recon = CaseReconciliation(court_case_id=case.id,
                                        previous_amount_assessed=case.amount_assessed,
                                        previous_amount_collected=case.amount_collected,
                                        previous_amount_owed=case.amount_owed,
                                        updated_amount_assessed=Decimal(
                                            ccam_case_balances.loc['Total Owed'].item()).quantize(cents, ROUND_HALF_UP),
                                        updated_amount_collected=Decimal(
                                            ccam_case_balances.loc['Total Collected'].item()).quantize(cents,
                                                                                                       ROUND_HALF_UP),
                                        updated_amount_owed=Decimal(
                                            ccam_case_balances.loc['Total Outstanding'].item()).quantize(cents,
                                                                                                         ROUND_HALF_UP))

        # Update DB
        case.amount_assessed = case_recon.updated_amount_assessed
        case.amount_collected = case_recon.updated_amount_collected
        case.amount_owed = case_recon.updated_amount_owed
        if case.amount_owed == 0:
            case.case_comment = 'PAID'
        dbsession.add_all([case, case_recon])


@async_timed()
async def main():
    _backup_db()
    prisoners = get_prisoners_from_db()
    cases_dict = {case.ccam_case_num: case for p in prisoners for case in p.cases_list}
    cases_dict = dict(sorted(cases_dict.items()))
    cases_for_reconciliation = [case.ccam_case_num for case in cases_dict.values() if case.case_comment == 'ACTIVE']
    print(f'Number of cases to reconcile: {len(cases_dict)}')
    session = AsyncHttpClient()
    await session.start()
    results = await session.get_CCAM_balances_async({'caseNumberList': cases_for_reconciliation})
    await session.stop()
    ccam_data, party_codes = sum_account_balances(results)

    for case in cases_for_reconciliation:
        try:
            ccam_balance = ccam_data.loc[str.split(case, '-')[0]]
            case_balance = cases_dict[case]
            reconcile_balances(case_balance, ccam_balance)
        except KeyError:
            print(f'CCAM balance not found for {case}')
            continue
    dbsession.commit()
    dbsession.close()


if __name__ == '__main__':
    asyncio.run(main())
