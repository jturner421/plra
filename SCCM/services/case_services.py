import os
from decimal import Decimal, ROUND_HALF_UP

import pydantic.errors
import SCCM.services.dataframe_cleanup as dc
import SCCM.schemas.case_schema as cs
from SCCM.schemas.balance import Balance




def get_prisoner_case_numbers(p, filter_list):
    """
    Identifies active cases for prisoner. Retrieves from network share

    :return: oldest active case
    """
    print(f'Getting existing cases for {p.legal_name} from network share')

    cases = [f.name for f in os.scandir(p.case_search_dir) if f.is_dir()]
    active_cases = cases[:]
    for case in cases:
        if any(s in case for s in filter_list):
            active_cases.remove(case)
    active_cases.sort()
    for c in active_cases:
        try:
            p.cases_list.append(cs.CaseCreate(
                ecf_case_num=str.upper(c),
                case_comment='ACTIVE')
            )

        # special processing for cases for multiple prisoner cases
        except pydantic.ValidationError:
            str_split = c.split('-')
            case_party_number = str_split[-1]
            ecf_case_num = "-".join(str_split[0:3])
            p.cases_list.append(cs.CaseCreate(
                ecf_case_num=str.upper(ecf_case_num),
                case_comment='ACTIVE',
                case_party_number=case_party_number
            ))
    return p


def initialize_balances(case, cases_dict, ccam_summary_balance, cents):
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
    return case