from __future__ import annotations
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import argparse
import os
from pathlib import Path

import SCCM.services.initiate_global_db_session
from SCCM.models import case_transaction
from SCCM.models.court_cases import CourtCase
from SCCM.services.crud import update_case_balances, create_prisoner, add_cases_for_prisoner, update_case_transactions
from SCCM.services.db_session import DbSession
from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, get_files as gf
from SCCM.services.case_services import initialize_balances

from SCCM.schemas.balance import Balance
import SCCM.bin.payment_strategy as payment
from SCCM.config.config_model import PLRASettings
from SCCM.bin.ccam_lookup import CCAMSettings
import SCCM.schemas.prisoner_schema as pSchema
import SCCM.services.prisoner_services as ps
import SCCM.services.case_services as cs
from SCCM.services.database_services import prod_db_backup
from SCCM.services.payment_services import prepare_ccam_upload_transactions, check_sum, prepare_deposit_number, \
    get_check_sum
from SCCM.services import crud, dataframe_cleanup as dc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Enter mode [dev,test,prod] for execution")
    args = parser.parse_args()

    if args.mode == 'dev':
        config_file = Path.cwd() / 'config' / 'dev.env'
        # config_file = 'SCCM/config/dev.env'
        settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

    db_session = DbSession.factory()
    # ccam_settings = CCAMSettings(_env_file='SCCM/ccam.env', _env_file_encoding='utf-8')
    filter_list = dc.populate_cases_filter_list()
    # Ask user to choose one or more files for processing
    filenames = gf.choose_files_for_import()

    for idx, file in enumerate(filenames):
        wb = cte.open_xls_file(file)
        sheet = wb['Sheet']
        check_date = datetime.today().strftime('%m/%d/%Y')
        check_amount = sheet['K2'].value
        check_number = sheet['L2'].value
        state_check_data = cte.convert_sheet_to_dataframe(sheet)

        state_check_data = dc.aggregate_prisoner_payment_amounts(state_check_data)

        cents, total_by_name_sum = get_check_sum(state_check_data)

        # check that dataframe aggregation matches original Excel sum
        check_amount = Decimal(check_amount).quantize(cents, ROUND_HALF_UP)
        # TODO Add function for handling aliases.  Examples:
        # Sovereignty Joseph Helmueller Sovereign is Andrew Helmueller
        # Brandon D. Bradley, Sr. aka Brittney Bradley

        check_sum(check_amount, total_by_name_sum)

        # format constants for Excel output
        deposit_num = prepare_deposit_number(check_date)

        # create Microsoft Excel upload file
        output_path = cte.create_output_path(file)
        excel_file = cte.create_output_file(check_date, check_number, output_path)

        # set dataframe index to payee DOC#
        state_check_data = state_check_data.set_index('DOC')

        # convert Pandas dataframe to dictionary
        prisoner_dict = state_check_data.to_dict('index')

        # make backup of SQLite DB
        original = f'{settings.db_base_directory}{settings.db_file}'
        destination = f'{settings.db_backup_directory}/{settings.db_file}_{check_number}'
        # Only make backup of DB the first time
        if not os.path.exists(destination):
            prod_db_backup(original, destination)

        # Instantiate prisoner objects
        prisoner_list = []
        for i, (key, value) in enumerate(prisoner_dict.items()):
            items = {
                "doc_num": key,
                "legal_name": value['Name'],
                "amount_paid": Decimal(value['Amount']).quantize(cents, ROUND_HALF_UP)
            }
            prisoner_list.append(pSchema.PrisonerCreate(**items))

        # Update models elements for payees and retrieve balances from internal DB if exists or CCAM API if not
        db_prisoner_list = []  # list to hold existing prisoners
        for i, p in enumerate(prisoner_list):
            try:
                amount_paid = p.amount_paid
                # retrieve prisoner from internal DB
                prisonerOrm = crud.get_prisoner_with_active_case(p.doc_num, p.legal_name)

                # initialization path for prisoner that exists in the database
                if prisonerOrm:
                    try:
                        p = ps.add_prisoner_to_db_session(settings.network_base_directory, p)
                        # check if new cases added on the network for existing prisoner
                        p = cs.get_prisoner_case_numbers(p, filter_list, prisonerOrm)
                        # add current cases from prisonerOrm to p.cases_list
                        # check if p.cases_list is empty
                        if not p.cases_list:
                            p.cases_list.extend(prisonerOrm.cases_list)
                        # if len(p.cases_list) > len(prisonerOrm.cases_list):
                        if len(p.cases_list) >= 1:
                            session = DbSession.factory()
                            session.add(prisonerOrm)
                            s = set(x.ecf_case_num for x in prisonerOrm.cases_list)
                            new_cases = [x for x in p.cases_list if x.ecf_case_num not in s]
                            if len(new_cases) >= 1:
                                cases_dict = {case.ecf_case_num: cte.format_case_num(case) for case in new_cases}
                                ccam_cases_to_retrieve = [value for (key, value) in cases_dict.items()]
                                ccam_balances = ccam.get_ccam_account_information(ccam_cases_to_retrieve,
                                                                                  settings=settings,
                                                                                  name=p.legal_name,
                                                                                  ecf_case_num=p.cases_list)
                                if ccam_balances:
                                    ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)

                                for case in new_cases:
                                    case = initialize_balances(case, cases_dict, ccam_summary_balance, cents)
                                    prisonerOrm.cases_list.append(CourtCase(acct_cd=case.acct_cd,
                                                                            amount_assessed=case.balance.amount_assessed,
                                                                            amount_collected=case.balance.amount_collected,
                                                                            amount_owed=case.balance.amount_owed,
                                                                            case_comment=case.case_comment,
                                                                            ccam_case_num=case.ccam_case_num,
                                                                            ecf_case_num=case.ecf_case_num))

                                    session.commit()
                                # save to list for future lookup
                        db_prisoner_list.append(prisonerOrm)

                    except Exception as e:
                        print(f'Error updating prisoner {p.legal_name} in database: {e}')
                        continue

                    # # convert to pydantic model for further processing
                    p = pSchema.PrisonerModel.from_orm(prisonerOrm)
                    p.amount_paid = amount_paid

                    for case in p.cases_list:
                        if case.case_comment == 'ACTIVE':
                            case.balance = Balance()
                            case.balance.amount_assessed = Decimal(case.amount_assessed.quantize(cents, ROUND_HALF_UP))
                            case.balance.amount_collected = Decimal(
                                case.amount_collected.quantize(cents, ROUND_HALF_UP))
                            case.balance.amount_owed = Decimal(case.amount_owed.quantize(cents, ROUND_HALF_UP))
                        prisoner_found = True
                    # swap with prisoner created in earlier step.  Only necessary for existing prisoners
                    prisoner_list[i] = p
                    prisoner_found = True

                else:
                    prisoner_found = False

            except Exception as e:
                print(f'Error processing prisoner {p.legal_name} in database: {e}')
                continue

            # initialization path for prisoner that does not exist in the database
            if not prisoner_found:
                p = ps.add_prisoner_to_db_session(settings.network_base_directory, p)
                p = cs.get_prisoner_case_numbers(p, filter_list, prisonerOrm)
                cases_to_skip = []
                cases_dict = {case.ecf_case_num: cte.format_case_num(case) for case in p.cases_list}

                ccam_cases_to_retrieve = [value for (key, value) in cases_dict.items()]
                if ccam_cases_to_retrieve:
                    ccam_balances = ccam.get_ccam_account_information(ccam_cases_to_retrieve, settings=settings,
                                                                      name=p.legal_name)
                    ccam_summary_balance, party_code = ccam.sum_account_balances(ccam_balances)
                for case in p.cases_list:
                    try:
                        case = initialize_balances(case, cases_dict, ccam_summary_balance, cents)
                        if case.case_comment == 'PAID':
                            cases_to_skip.append(case)

                    except KeyError:
                        cases_to_skip.append(case)
                        pass

                if len(cases_to_skip) > 0:
                    for case in cases_to_skip:
                        if case in p.cases_list:
                            p.cases_list.remove(case)
                if party_code:
                    p.vendor_code = party_code

            # Process Payments and identify overpayments
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

    # Process new transactions for Excel output
    payment_records = prepare_ccam_upload_transactions(prisoner_list)

    # Create CCAM upload file in Excel format
    cte.write_rows_to_output_file(excel_file, payment_records, deposit_num, check_date)

    # add prisoners to database
    print('Adding prisoners to database. Check Excel File for errors.')
    # input('Press Enter to continue...')
    # TODO Adjust session to be a single session for all prisoners
    with DbSession.factory() as session:
        session.begin()
        try:
            for p in prisoner_list:
                if p.exists:
                    # from SCCM.models.prisoners import Prisoner
                    # result = session.query(Prisoner).filter(Prisoner.doc_num == p.doc_num).first()
                    # session.add(result)

                    new_transactions = [case for case in p.cases_list if case.transaction]
                    for t in new_transactions:
                        case_db = update_case_balances(t, db_prisoner_list)
                        session.add(case_db)
                        case_db.case_transactions.append(case_transaction.CaseTransaction(
                            check_number=case.transaction.check_number,
                            amount_paid=case.transaction.amount_paid
                        ))


                else:
                    db_prisoner = create_prisoner(p)
                    session.add(db_prisoner)
                    db_prisoner = add_cases_for_prisoner(db_prisoner, p)
                    # session.add(db_prisoner)
        except:
            session.rollback()
            raise
        else:
            session.commit()


if __name__ == '__main__':
    main()
