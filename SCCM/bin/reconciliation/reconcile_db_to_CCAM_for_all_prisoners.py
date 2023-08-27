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
import asyncio

from colorama import Fore
from pandas import DataFrame
from SCCM.models.court_cases import CourtCase
from SCCM.services.db_session import DbSession
from SCCM.config.config_model import PLRASettings
from SCCM.services.database_services import prod_db_backup
from SCCM.models.prisoners import Prisoner
from SCCM.schemas.balance import Balance
from SCCM.bin import ccam_lookup as ccam
from SCCM.util import async_timed
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
    prisoners = dbsession.query(Prisoner).options(selectinload(Prisoner.cases_list)).limit(15).all()
    # prisoners = session.query(Prisoner).options(selectinload(Prisoner.cases_list)).all()
    return prisoners


async def generate_data(tasks: list[tuple[CourtCase, Prisoner, asyncio.coroutines]], data: asyncio.Queue) -> None:
    """
    Places tasks into asyncio queue up to the limit specified in main()
    :param tasks: list of tuples that contains case, prisoner, and coroutine to retrieve CCAM balances for that case
    :param data: asyncio queue
    :return: None
    """
    for t in tasks:
        # Use the asyncio Queue
        work = (t, datetime.now())
        await data.put(work)
        print(Fore.YELLOW + f" -- generated item {t[0]}", flush=True)
        # await asyncio.sleep(random() + .5)


async def process_data(data: asyncio.Queue, i: int) -> None:
    """
    Processes data from asyncio queue. Retrieves CCAM balances for each case and compares to database balances. If there
    is a mismatch, the database is updated and a reconciliation transaction is created.
    :param data: asyncio queue
    :param i: worker number
    :return: None
    """
    while not data.empty():
        item = await data.get()
        case = item[0][0]
        ccam_balances = await item[0][2]
        ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)
        case_db_balances, ccam_case_balances = create_balance_comparison(case, ccam_summary_balance)
        reconcile_balances(case, case_db_balances, ccam_case_balances)


async def get_ccam_account_information(case, p, data: asyncio.Queue) -> list[dict]:
    """
    Retrieves CCAM balances for a case from JIFMS

    :param case: Case object
    :param p: Prisoner object
    :param data: asyncio queue
    :return: list of Dictionaries of CCAM balances
    """
    ccam_balances = await ccam.async_get_ccam_account_information(case.ccam_case_num, settings=settings,
                                                                  name=p.legal_name, ecf_case_num=case.ecf_case_num)
    return ccam_balances


def create_balance_comparison(case: CourtCase, ccam_summary_balance: DataFrame) -> tuple[Balance, Balance]:
    """
    Creates balance objects for CCAM and database values.
    :param case: case object
    :param ccam_summary_balance: Dataframe of CCAM balances
    :return:
    """
    ccam_case_balances = Balance()
    ccam_case_balances.add_ccam_balances(ccam_summary_balance)
    case_db_balances = Balance(amount_assessed=case.amount_assessed,
                               amount_collected=case.amount_collected,
                               amount_owed=case.amount_owed)
    return case_db_balances, ccam_case_balances


def reconcile_balances(case: CourtCase, case_db_balances: Balance, ccam_case_balances: Balance) -> None:
    """
    Compares CCAM and database balances. If they do not match, the database is updated and a reconciliation transaction
    :param case: case object
    :param case_db_balances: Database balances
    :param ccam_case_balances: CCAM balances
    :return: None
    """
    try:
        assert ccam_case_balances == case_db_balances
        print(Fore.BLUE + f'Balances match for {case.prisoner.legal_name} - {case.ecf_case_num}\n')
    except AssertionError:
        print(Fore.RED + f'Balances do not match {case.prisoner.legal_name} - {case.ecf_case_num}')
        print(f'CCAM: {ccam_case_balances}')
        print(f'Database: {case_db_balances}')
        print('')
        print(f'Updating Database for {case.prisoner.legal_name} - {case.ecf_case_num}')
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


@async_timed()
async def main():
    _backup_db()
    prisoners = get_prisoners_from_db()
    cases = [case for p in prisoners for case in p.cases_list]
    data = asyncio.Queue(4)
    tasks = [(case, case.prisoner, get_ccam_account_information(case, case.prisoner, data)) for case in cases]
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(generate_data(tasks, data))
        task2 = [tg.create_task(process_data(data, i)) for i in range(2)]
    dbsession.commit()
    dbsession.close()


if __name__ == '__main__':
    asyncio.run(main())
