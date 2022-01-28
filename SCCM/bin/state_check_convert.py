from __future__ import annotations
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import argparse

from SCCM.services.case_services import initialize_balances
from SCCM.services.db_session import DbSession
from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, dataframe_cleanup as dc, \
    get_files as gf

from SCCM.models.balance import Balance
import SCCM.bin.payment_strategy as payment
from SCCM.config.config_model import PLRASettings
from SCCM.bin.ccam_lookup import CCAMSettings
import SCCM.models.prisoner_schema as pSchema
import SCCM.services.prisoner_services as ps
import SCCM.services.case_services as cs
from SCCM.services.database_services import prod_db_backup
from SCCM.services.payment_services import prepare_ccam_upload_transactions, check_sum, prepare_deposit_number, \
    get_check_sum
from SCCM.services import crud


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Enter mode [dev,test,prod] for execution")
    args = parser.parse_args()

    if args.mode == 'dev':
        config_file = '../config/dev.env'
        settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

    db_session = DbSession.factory()
    ccam_settings = CCAMSettings(_env_file='../ccam.env', _env_file_encoding='utf-8')

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

        # Update data elements for payees and retrieve balances from internal DB if exists or CCAM API if not
        # list to hold existing prisoners
        db_prisoner_list = []
        for i, p in enumerate(prisoner_list):
            try:
                amount_paid = p.amount_paid
                prisonerOrm = crud.get_prisoner_with_active_case(db_session, p.doc_num, p.legal_name)

                # initialization path for prisoner that exists in the database
                if prisonerOrm:
                    # save to list for future lookup
                    db_prisoner_list.append(prisonerOrm)

                    # convert to pydantic model for further processing
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
                else:
                    prisoner_found = False

            except NoResultFound:
                prisoner_found = False

            # initialization path for prisoner that does not exist in the database
            if not prisoner_found:
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
                       case = initialize_balances(case, cases_dict, ccam_summary_balance, cents)

                    except KeyError:
                        cases_to_skip.append(case)
                        pass

                if len(cases_to_skip) > 0:
                    for case in cases_to_skip:
                        if case in p.cases_list:
                            p.cases_list.remove(case)
                if party_code:
                    p.vendor_code = party_code

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

    payment_records = prepare_ccam_upload_transactions(prisoner_list)

    cte.write_rows_to_output_file(excel_file, payment_records, deposit_num, check_date)

    # add prisoners to database
    crud.add_transactions_to_database(db_session, prisoner_list, db_prisoner_list)


if __name__ == '__main__':
    main()
