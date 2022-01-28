import pandas as pd
from decimal import Decimal
from decimal import ROUND_HALF_UP

from SCCM.services.db_session import DbSession
from SCCM.config.config_model import PLRASettings
from SCCM.bin.ccam_lookup import CCAMSettings
from SCCM.bin import convert_to_excel as cte, ccam_lookup as ccam, get_files as gf

from SCCM.models.prisoner_schema import PrisonerCreate
from SCCM.services import crud


def main():
    # Get configuration and establish sessions
    config_file = '../../config/dev.env'
    settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')
    ccam_settings = CCAMSettings(_env_file='../../ccam.env', _env_file_encoding='utf-8')
    db_path = f'{settings.db_base_directory}{settings.db_file}'
    DbSession.global_init(db_path)
    db_session = DbSession.factory()
    cents = Decimal('0.01')

    # Ask user to choose one or more files for processing
    filenames = gf.choose_files_for_import()

    for idx, file in enumerate(filenames):
        # Prepare data from Excel check file
        wb = cte.open_xls_file(file)
        sheet = wb['Sheet']
        df = pd.DataFrame(sheet.values)
        state_check_data = df[[1, 2]]
        state_check_data.columns = ['DOC', 'Name']
        state_check_data = state_check_data.drop(0)
        state_check_data.drop_duplicates(inplace=True)
        state_check_data.set_index(state_check_data['Name'], inplace=True)
        state_check_data.drop('Name', axis=1, inplace=True)
        prisoner_names_dict = state_check_data.to_dict(orient='index')

        # Create prisone objects
        prisoner_list = []
        for i, (key, value) in enumerate(prisoner_names_dict.items()):
            items = {
                "doc_num": value['DOC'],
                "legal_name": key,
                "amount_paid": 0
            }
            prisoner_list.append(PrisonerCreate(**items))

        # Get case information and retreive balances from CCAM
        import SCCM.services.prisoner_services as ps
        import SCCM.services.case_services as cs
        from SCCM.models.balance import Balance
        for i, p in enumerate(prisoner_list):
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
                    case.balance.amount_owed = Decimal(ccam_balance['Total Outstanding']).quantize(cents,ROUND_HALF_UP)

                except KeyError:
                    cases_to_skip.append(case)
                    pass

            if len(cases_to_skip) > 0:
                for case in cases_to_skip:
                    if case in p.cases_list:
                        p.cases_list.remove(case)
            if party_code:
                p.vendor_code = party_code

            db_prisoner = crud.create_prisoner(db_session, p)
            crud.add_cases_for_prisoner(db_session, db_prisoner, p)
        db_session.commit()

if __name__ == '__main__':
    main()
