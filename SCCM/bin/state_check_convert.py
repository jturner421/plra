from __future__ import annotations
from datetime import datetime
from decimal import *
import sqlite3
import os
import argparse

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, dataframe_cleanup as dc, \
    get_files as gf, prisoners
from SCCM.data.db_session import DbSession
from SCCM.data.case_balance import CaseBalance
from SCCM.data.court_cases import CourtCase
from SCCM.data.prisoners import Prisoner
from SCCM.models.balance import Balance
import SCCM.bin.payment_strategy as payment
from SCCM.config.config_model import PLRASettings
from SCCM.bin.ccam_lookup import CCAMSettings


def check_sum(check_amount, total_by_name_sum):
    try:
        assert total_by_name_sum == check_amount
        print(
            f'Check amount of {check_amount:,.2f} matches the sum of the converted file - {total_by_name_sum:,.2f}')
    except AssertionError:
        print(
            f"ERROR: The sum of the file header:{check_amount:,.2f} does not match the sum:{total_by_name_sum:,.2f}"
            f" of the converted file.")


def convert_sheet_to_dataframe(sheet):
    """
    Takes Openpyxl sheet with prisoner payments, converts to panda dataframe, and cleans up for futher processing
    :param sheet: Sheet object containing prisoner payment data
    :return: dataframe of payments
    """
    df = pd.DataFrame(sheet.values)
    dframe = df[[1, 2, 7]]
    dframe.columns = ['DOC', 'Name', 'Amount']
    dframe = dframe.drop(0)
    return dframe


def progress(status, remaining, total):
    print('Backing up Database')
    print(f'Copied {total - remaining} of {total} pages...')


def prod_db_backup(original, destination):
    db_orig = sqlite3.connect(original)
    db_backup = sqlite3.connect(destination)
    with db_backup:
        db_orig.backup(db_backup, pages=1, progress=progress)
    db_backup.close()
    db_orig.close()


def prod_db_restore(db_file, destination, db_backup_path, db_backup_file_name):
    print('An errror processing this check has occured. \n')
    db_orig = sqlite3.connect(db_file)

    backup = f'{db_backup_path}{db_backup_file_name}_backup.db'
    db_backup = sqlite3.connect(backup)
    db_restore = sqlite3.connect(destination)

    # first make a backup of the current state
    with db_orig:
        db_orig.backup(db_backup, pages=1)
    # Delete the db file
    os.remove(db_file)

    # Copy the restore DB to the original file name
    db_orig = sqlite3.connect(db_file)
    print('Restoring database to previous state.\n')
    with db_restore:
        db_restore.backup(db_orig, pages=1)

    db_backup.close()
    db_orig.close()
    db_restore.close()


def insert_new_case_with_balances(base_url, db_session, p, prisoner, session,
                                  db_file, destination, db_backup_path, db_backup_file_name):
    try:
        for c in p.cases_list:
            print(f'Populating case balances for {c}')
            prisoner.cases.append(CourtCase(prisoner_doc_num=p.doc_num, case_num=c))

            formatted_case_number = cte.format_case_num(prisoner.cases[-1].ecf_case_num)
            ccam_balance = ccam.get_ccam_account_information(formatted_case_number)
            prisoner.cases[-1].acct_cd = ccam_balance['data'][0]['acct_cd']
            prisoner.cases[-1].case_comment = 'ACTIVE'
            # TODO create case class with composition to prisoner
            ccam.sum_account_balances(ccam_balance, p)
            # populate balances for cases in person object
            prisoner.cases[-1].case_balance.append(
                CaseBalance(court_case_id=prisoner.cases[-1].id,
                            amount_assessed=p.ccam_balance["Total Owed"],
                            amount_collected=p.ccam_balance["Total Collected"],
                            amount_owed=p.ccam_balance["Total Outstanding"]))
            # db_session.add(prisoner.court_cases[-1])
            # db_session.commit()
        p.cases_list = db_session.query(CourtCase).filter(CourtCase.prisoner_doc_num == int(p.doc_num)).all()
        return p, prisoner
    except TypeError:
        prod_db_restore(db_file, destination, db_backup_path, db_backup_file_name)
        exit(1)


def add_prisoner_to_db(network_base_dir, p):
    print(f'{p.check_name} not found in database. Creating.... ')
    # Get parameters, create new user, insert into DB and load balances
    # search for name on network share
    p.drop_suffix_from_name(dc.populate_suffix_list())
    p.search_dir = p.construct_search_directory_for_prisoner(network_base_dir)
    p.plra_name = p.get_name_ratio()
    p.case_search_dir = f"{p.search_dir}/{p.plra_name}"
    # get the existing cases

    # insert the prisoner into the database
    # p.create_prisoner(db_session, session, base_url)
    # doc_num = input(f'Enter DOC Number for {p.plra_name}: ')
    # prisoner_db = Prisoner(doc_num=int(p.doc_num), legal_name=p.check_name, judgment_name=p.check_name)
    # db_session.add(prisoner_db)
    # p.new_cases_list = p.cases_list
    # p, prisoner = insert_new_case_with_balances(base_url, db_session, p, prisoner_db, session,
    #                                             db_file, destination, db_backup_path, db_backup_file_name)
    return p


def get_existing_cases_from_network(p):
    print(f'Getting existing cases for {p.plra_name}')
    p.get_prisoner_case_numbers(dc.populate_cases_filter_list())
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Enter mode [dev,test,prod] for execution")
    args = parser.parse_args()

    if args.mode == 'dev':
        config_file = '../config/dev.env'
        settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

    # Initialize filter lists from database
    # suffix_list = dc.populate_suffix_list(db_session)
    # cases_filter_list = dc.populate_cases_filter_list(db_session)
    # Ask user to choose one or more files for processing
    filenames = gf.choose_files_for_import()

    for idx, file in enumerate(filenames):
        wb = cte.open_xls_file(file)
        sheet = wb['Sheet']
        check_date = datetime.today().strftime('%m/%d/%Y')
        check_amount = sheet['K2'].value
        check_number = sheet['L2'].value
        state_check_data = convert_sheet_to_dataframe(sheet)

        state_check_data = dc.aggregate_prisoner_payment_amounts(state_check_data)

        cents = Decimal('0.01')
        total_by_name_sum = state_check_data['Amount'].sum()
        total_by_name_sum = Decimal(total_by_name_sum).quantize(cents, ROUND_HALF_UP)

        # check that dataframe aggregation matches original Excel sum
        check_amount = Decimal(check_amount).quantize(cents, ROUND_HALF_UP)
        check_sum(check_amount, total_by_name_sum)

        # format constants for Excel output
        check_date_split = str.split(check_date, '/')
        deposit_num = f"PL{check_date_split[0]}{check_date_split[1]}{check_date_split[2][2:]}"

        # create Microsoft Excel upload file
        output_path = cte.create_output_path(file)
        excel_file = cte.create_output_file(check_date, check_number, output_path)

        # set dataframe index to payee DOC#
        state_check_data = state_check_data.set_index('DOC')

        # convert Pandas dataframe to dictionary
        prisoner_dict = state_check_data.to_dict('index')

        # make backup of SQLite DB
        original = f'{settings.db_base_directory}{settings.db_file}.db'
        destination = f'{settings.db_backup_directory}/{settings.db_file}_{check_number}.db'
        prod_db_backup(original, destination)

        # Instantiate prisoner objects
        prisoner_list = dict()
        for i, (key, value) in enumerate(prisoner_dict.items()):
            doc_num = key
            name = value['Name']
            amount = Decimal(value['Amount']).quantize(cents, ROUND_HALF_UP)
            prisoner_list[i] = prisoners.Prisoners(name, doc_num, amount)

        # Update data elements for payees and retrieve balances from internal DB if exists or CCAM API if not
        db_session = DbSession.global_init(f"{settings.db_base_directory}{settings.db_file}")
        for key, p in prisoner_list.items():
            # lookup name in internal DB for existance
            ccam_settings = CCAMSettings(_env_file='../ccam.env', _env_file_encoding='utf-8')
            try:
                stmt = select(Prisoner).filter_by(doc_num=int(p.doc_num))
                prisoner = db_session.execute(stmt).scalar_one()
                db_session.add(prisoner)
                prisoner_found = True

            except NoResultFound:
                prisoner_found = False
            if not prisoner_found:
                # retrieve cases and CCAM balances
                p = add_prisoner_to_db(settings.network_base_directory, p)
                p = get_existing_cases_from_network(p)
                cases_to_skip = []
                for i, case in enumerate(p.cases_list):
                    try:
                        case.formatted_case_num = cte.format_case_num(case.case_number)
                        case.balance = Balance()
                        ccam_balance = ccam.get_ccam_account_information(case, settings=ccam_settings)
                        # case.acct_cd = ccam_balance['data'][0]['acct_cd']
                        ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balance, case)
                        case.balance.add_ccam_balances(ccam_summary_balance)
                    except IndexError:
                        if not ccam_balance['data']:
                            cases_to_skip.append(case)
                            pass

                if len(cases_to_skip) > 0:
                    for case in cases_to_skip:
                        if case in p.cases_list:
                            p.cases_list.remove(case)
                else:
                    p.pty_cd = party_code

            # db_session.add(Prisoner(doc_num=p.doc_num, judgment_name=p.plra_name, legal_name=p.check_name,
            #                         vendor_code=p.pty_cd))

            # Process Payments and find overpayments
            number_of_cases_for_prisoner = len(p.cases_list)
            if number_of_cases_for_prisoner == 0:
                context = payment.Context(payment.OverPaymentProcess())
                p = context.process_payment(p, int(check_number))

            elif number_of_cases_for_prisoner > 1:
                context = payment.Context(payment.MultipleCasePaymentProcess())
                p = context.process_payment(p, int(check_number))

            else:
                context = payment.Context(payment.SingleCasePaymentProcess())
                p = context.process_payment(p, int(check_number))

    # Save excel file for upload to JIFMS
    payments = []
    for key, p in prisoner_list.items():
        for case in p.cases_list:
            if case.transaction or case.overpayment:
                payments.append({'prisoner': p, 'case': case})

    cte.write_rows_to_output_file(excel_file, payments, deposit_num, check_date)




if __name__ == '__main__':
    main()
