from __future__ import annotations
from datetime import datetime
from decimal import *
import sqlite3
import os
import argparse

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
import SCCM.data.initiate_global_db_session
from SCCM.data.db_session import DbSession
from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, dataframe_cleanup as dc, \
    get_files as gf

from SCCM.data.court_cases import CourtCase
from SCCM.data.prisoners import Prisoner
from SCCM.models.balance import Balance
import SCCM.bin.payment_strategy as payment
from SCCM.config.config_model import PLRASettings
from SCCM.bin.ccam_lookup import CCAMSettings
import SCCM.models.prisoner_schema as pSchema
import SCCM.services.prisoner_services as ps
import SCCM.services.case_services as cs
from SCCM.services.payment_services import prepare_ccam_upload_transactions
from SCCM.services import crud


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Enter mode [dev,test,prod] for execution")
    args = parser.parse_args()

    if args.mode == 'dev':
        config_file = '../config/dev.env'
        settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

    db_session = DbSession.factory()

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
        prisoner_list = []
        for i, (key, value) in enumerate(prisoner_dict.items()):
            items = {
                "doc_num": key,
                "legal_name": value['Name'],
                "amount_paid": Decimal(value['Amount']).quantize(cents, ROUND_HALF_UP)
            }
            # prisoner_list[i] = pSchema.PrisonerCreate(**items)
            prisoner_list.append(pSchema.PrisonerCreate(**items))

        # Update data elements for payees and retrieve balances from internal DB if exists or CCAM API if not
        db_prisoner_list = []
        for i, p in enumerate(prisoner_list):
            # lookup name in internal DB for existance
            ccam_settings = CCAMSettings(_env_file='../ccam.env', _env_file_encoding='utf-8')
            try:
                # stmt = select(Prisoner).filter_by(doc_num=int(p.doc_num))
                # stmt = select(Prisoner).where(Prisoner.doc_num == p.doc_num)
                # prisoner = db_session.execute(stmt).scalar_one()
                amount_paid = p.amount_paid
                prisonerOrm = crud.get_prisoner(db_session, p.doc_num)
                if prisonerOrm:
                    db_prisoner_list.append(prisonerOrm)
                    p = pSchema.PrisonerModel.from_orm(prisonerOrm)
                    p.amount_paid = amount_paid

                    for case in p.cases_list:
                        case.balance = Balance()
                        case.balance.amount_assessed = Decimal(case.amount_assessed.quantize(cents, ROUND_HALF_UP))
                        case.balance.amount_collected = Decimal(case.amount_collected.quantize(cents, ROUND_HALF_UP))
                        case.balance.amount_owed = Decimal(case.amount_owed.quantize(cents, ROUND_HALF_UP))

                        prisoner_found = True
                    prisoner_list[i] = p
                else:
                    prisoner_found = False

            except NoResultFound:
                prisoner_found = False
            if not prisoner_found:
                # retrieve cases and CCAM balances
                p = ps.add_prisoner_to_db_session(settings.network_base_directory, p)
                p = cs.get_prisoner_case_numbers(p)
                cases_to_skip = []
                cases_dict = {case.ecf_case_num: cte.format_case_num(case) for case in p.cases_list}

                ccam_cases_to_retrieve = [value for (key, value) in cases_dict.items()]
                ccam_balances = ccam.get_ccam_account_information(ccam_cases_to_retrieve, settings=ccam_settings,
                                                                  name=p.legal_name)
                ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)
                for case in p.cases_list:
                    try:
                        case.balance = Balance()
                        balance_key = cases_dict[case.ecf_case_num].split('-')[0]
                        case.acct_cd = ccam_summary_balance.loc[balance_key]['acct_cd']
                        case.ccam_case_num = cases_dict[case.ecf_case_num]
                        ccam_balance = ccam_summary_balance.loc[balance_key].to_dict()
                        case.balance.amount_assessed = Decimal(ccam_balance['Total Owed']).quantize(cents,
                                                                                                    ROUND_HALF_UP)
                        case.balance.amount_collected = Decimal(ccam_balance['Total Collected']).quantize(cents,
                                                                                                          ROUND_HALF_UP)
                        case.balance.amount_owed = Decimal(ccam_balance['Total Outstanding']).quantize(cents,
                                                                                                       ROUND_HALF_UP)
                        # case.balance.add_ccam_balances(ccam_summary_balance.loc[balance_key].to_dict())

                    except KeyError:
                        cases_to_skip.append(case)
                        pass

                if len(cases_to_skip) > 0:
                    for case in cases_to_skip:
                        if case in p.cases_list:
                            p.cases_list.remove(case)
                if party_code:
                    p.vendor_code = party_code

            # db_session.add(Prisoner(doc_num=p.doc_num, judgment_name=p.plra_name, legal_name=p.legal_name,
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

    payments = prepare_ccam_upload_transactions(prisoner_list)

    cte.write_rows_to_output_file(excel_file, payments, deposit_num, check_date)

    # add prisoners to database

    for p in prisoner_list:
        if p.exists:
            new_transactions = [case for case in p.cases_list if case.transaction]
            for t in new_transactions:
                crud.update_case_balances(db_session, t, db_prisoner_list)
        else:
            db_prisoner = crud.create_prisoner(db_session, p)
            crud.add_cases_for_prisoner(db_session, db_prisoner, p)
    db_session.commit()


if __name__ == '__main__':
    main()
