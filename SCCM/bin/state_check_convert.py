import shutil
from datetime import datetime
from decimal import *
from pathlib import Path
import sqlite3
import os

import keyring
import pandas as pd
import requests
from dotenv import load_dotenv

from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, dataframe_cleanup as dc, \
    get_files as gf, prisoners
from SCCM.config import config
from SCCM.data.case_balance import CaseBalance
from SCCM.data.case_filter import CaseFilter
from SCCM.data.court_cases import CourtCase
from SCCM.data.db_session import DbSession
from SCCM.data.prisoners import Prisoner

db_session = ''


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


def prod_db_backup(db_file, destination):
    db_orig = sqlite3.connect(db_file)
    db_backup = sqlite3.connect(destination)
    with db_backup:
        db_orig.backup(db_backup, pages=1, progress=progress)
    db_backup.close()
    db_orig.close()


def prod_db_restore(db_file, destination, db_backup_path,db_backup_file_name ):
    print('An errror processing this check has occured. \n')
    db_orig = sqlite3.connect(db_file)

    backup = f'{db_backup_path}{db_backup_file_name}_backup.db'
    db_backup = sqlite3.connect(backup)

    # restore = f'{db_backup_path}{db_backup_file_name}_{check_number}.db'
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
        for c in p.new_cases_list:
            print(f'Populating case balances for {c}')
            prisoner.court_cases.append(CourtCase(prisoner_doc_num=p.doc_num, case_num=c))

            formatted_case_number = cte.format_case_num(prisoner.court_cases[-1].case_num)
            ccam_balance = ccam.get_ccam_account_information(formatted_case_number, session, base_url)
            prisoner.court_cases[-1].acct_cd = ccam_balance['data'][0]['acct_cd']
            prisoner.court_cases[-1].case_comment = 'ACTIVE'
            ccam.sum_account_balances(ccam_balance, p)
            # populate balances for cases in person object
            prisoner.court_cases[-1].case_balance.append(
                CaseBalance(court_case_id=prisoner.court_cases[-1].id,
                            amount_assessed=p.ccam_balance["Total Owed"],
                            amount_collected=p.ccam_balance["Total Collected"],
                            amount_owed=p.ccam_balance["Total Outstanding"]))
            # db_session.add(prisoner.court_cases[-1])
            db_session.commit()
        p.cases_list = db_session.query(CourtCase).filter(CourtCase.prisoner_doc_num == int(p.doc_num)).all()
        return p, prisoner
    except TypeError:
        prod_db_restore(db_file, destination, db_backup_path,db_backup_file_name)
        exit(1)

def main():
    # read config file
    config_path = Path('/Users/jwt/PycharmProjects/plra/SCCM')
    config_file = config_path / 'config' / 'config.ini'
    configuration = config.initialize_config(str(config_file))
    load_dotenv()

    # Initialize session variables contained in config.ini
    prod_vars = config.get_prod_vars(configuration, 'PROD')
    network_base_dir = prod_vars['NETWORK_BASE_DIR']
    prod_db_path = prod_vars['NETWORK_DB_BASE_DIR']
    db_file_name = prod_vars['DATABASE_SQLite']
    db_file = f'{prod_db_path}{db_file_name}'
    db_session = DbSession.global_init(db_file)
    ccam_username = prod_vars['CCAM_USERNAME']
    base_url = prod_vars['CCAM_API']
    # ccam_password = keyring.get_password("WIWCCA", ccam_username)
    ccam_password = os.getenv('CCAM_PASSWORD')
    session = requests.Session()
    session.auth = (ccam_username, ccam_password)
    cert_path = prod_vars['CLIENT_CERT_PATH']
    session.verify = cert_path

    # Initialize filter lists from database
    suffix_list = dc.populate_suffix_list(db_session)
    cases_filter_list = dc.populate_cases_filter_list(db_session)

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
        check_amount = Decimal(check_amount).quantize(cents, ROUND_HALF_UP)

        try:
            assert total_by_name_sum == check_amount
            print(
                f'Check amount of {check_amount:,.2f} matches the sum of the converted file - {total_by_name_sum:,.2f}')
        except AssertionError:
            print(
                f"ERROR: The sum of the file header:{check_amount:,.2f} does not match the sum:{total_by_name_sum:,.2f}"
                f" of the converted file.")

        # set dataframe index to payee DOC#
        state_check_data = state_check_data.set_index('DOC')

        # convert Panda object to dictionary
        prisoner_dict = state_check_data.to_dict('index')

        # make backup of SQLite DB
        db_backup_path = prod_vars['NETWORK_DB_BACKUP_DIR']
        db_backup_file_name = prod_vars['DATABASE_BACKUP_FILE_NAME']
        destination = f'{db_backup_path}db/backup/{db_backup_file_name}_{check_number}.db'
        # shutil.copyfile(db_file, destination)
        prod_db_backup(db_file, destination)

        # Instantiate prisoner objects
        prisoner_list = dict()
        for i, (key, value) in enumerate(prisoner_dict.items()):
            doc_num = key
            name = value['Name']
            amount = Decimal(value['Amount']).quantize(cents, ROUND_HALF_UP)
            prisoner_list[i] = prisoners.Prisoners(name, doc_num, amount)

        # format constants for Excel output
        check_date_split = str.split(check_date, '/')
        deposit_num = f"PL{check_date_split[0]}{check_date_split[1]}{check_date_split[2][2:]}"

        # create Microsoft Excel file
        output_path = cte.create_output_path(file)
        excel_file = cte.create_output_file(check_date, check_number, output_path)

        # Update data elements for payees and retrieve balances from internal DB if exists or CCAM API if not
        for key, p in prisoner_list.items():
            # lookup name in internal DB
            try:
                prisoner = db_session.query(Prisoner).get(int(p.doc_num))
                if prisoner:
                    db_session.add(prisoner)
                    # db_session.add(p)

                if prisoner is None:
                    print(f'{p.check_name} not found in database. Creating.... ')
                    # Get parameters, create new user, insert into DB and load balances
                    # search for name on network share
                    p.drop_suffix_from_name(suffix_list)
                    p.search_dir = p.construct_search_directory_for_prisoner(network_base_dir)
                    p.plra_name = p.get_name_ratio()
                    p.case_search_dir = f"{p.search_dir}/{p.plra_name}"

                    # get the existing cases
                    print(f'Getting existing cases for {p.plra_name}')
                    p.cases_list = p.get_prisoner_case_numbers(cases_filter_list)

                    # insert the prisoner into the database
                    # p.create_prisoner(db_session, session, base_url)
                    doc_num = input(f'Enter DOC Number for {p.plra_name}: ')
                    prisoner = Prisoner(doc_num=int(doc_num), legal_name=p.plra_name)
                    db_session.add(prisoner)
                    p.new_cases_list = p.cases_list
                    p, prisoner = insert_new_case_with_balances(base_url, db_session, p, prisoner, session,
                                                                db_file, destination, db_backup_path, db_backup_file_name)

                else:
                    # get active cases for payee

                    query = db_session.query(CaseFilter.filter_text).subquery()
                    p.cases_list = db_session.query(CourtCase).filter(CourtCase.prisoner_doc_num == int(p.doc_num)) \
                        .filter(CourtCase.case_comment.notin_(query)).all()
                    if not p.cases_list:
                        p.drop_suffix_from_name(suffix_list)
                        p.search_dir = p.construct_search_directory_for_prisoner(network_base_dir)
                        p.plra_name = p.get_name_ratio()
                        p.case_search_dir = f"{p.search_dir}/{p.plra_name}"

                        # get the cases from network share
                        p.new_cases_list = p.get_prisoner_case_numbers(cases_filter_list)
                        if not p.new_cases_list:
                            p.formatted_case_num = f'No Active Case Found for for payee {p.check_name}'
                            p.ccam_balance = {'Total Owed': 0.00, 'Total Collected': 0.00, 'Total Outstanding': 0.00}
                            p = ccam.check_for_overpayment(p)
                            continue

                        # for each case, get a case balance from CCAM

                        p, prisoner = insert_new_case_with_balances(base_url, db_session, p, prisoner, session,
                                                                    db_file, destination, db_backup_path, db_backup_file_name)

                        # reload case list
                        p.cases_list = db_session.query(CourtCase).filter(CourtCase.prisoner_doc_num == int(p.doc_num)) \
                            .filter(CourtCase.case_comment.notin_(query)).all()
                        # db_session.add(p)
                        # Update case account code or prisoner vendor code if needed
                        # FIXME -Ths code currently does not update the prty codes

                p.current_case = p.cases_list.pop()
                p.formatted_case_num = cte.format_case_num(p.current_case.case_num)
                # if not p.current_case.acct_cd:
                #     p.formatted_case_num = cte.format_case_num(p.current_case.case_num)
                #     codes = ccam.get_ccam_account_information(p.formatted_case_num, session, base_url)
                #     if codes['data']:
                #         p.current_case.acct_cd = codes['data'][0]['acct_cd']
                #         # p.pty_cd = codes['data'][0]['prty_cd']
                #         # p.update_pty_acct_cd(result, s)
                #     else:
                #         pass

                # Check for an overpayment
                p = ccam.check_for_overpayment(p)
                p.create_transaction(check_number, db_session)
                p.update_account_balance()
                # db_session.add()
                db_session.commit()
                if p.overpayment.exists:
                    print(f" The DOC # for {p.check_name} is {p.doc_num}."
                          f" An overpayment was made in the amount of $ {Decimal(p.overpayment.amount_overpaid).quantize(cents, ROUND_HALF_UP)}\n")
                else:
                    print(f" The DOC # for {p.check_name} is {p.doc_num}."
                          f" The amount paid is ${p.amount}\n")
                # TODO: add logic to check for next active open case
            except IndexError:
                p.formatted_case_num = f'No Active Case Found for for payee {p.check_name}'
                p.ccam_balance = {'Total Owed': 0.00, 'Total Collected': 0.00, 'Total Outstanding': 0.00}
                overpayment_exists = ccam.check_for_overpayment(p)
                p.overpayment = overpayment_exists
                continue
            except FileNotFoundError:
                prod_db_restore(db_file, destination, db_backup_path,db_backup_file_name)
                exit(1)

    # Save excel file for upload to JIFMS

    cte.write_rows_to_output_file(excel_file, prisoner_list, deposit_num, check_date)


if __name__ == '__main__':
    main()
