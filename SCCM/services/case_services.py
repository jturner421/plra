import os
from decimal import Decimal, ROUND_HALF_UP

import pydantic.errors
import SCCM.schemas.case_schema as cs
from SCCM.schemas.balance import Balance


def get_prisoner_case_numbers(p, filter_list, prisonerOrm):
    """
    Identifies active cases for prisoner. Retrieves from network share

    :return: oldest active case
    """
    print(f'Getting new cases for {p.legal_name} from network share')
    if prisonerOrm:
        active_cases, cases = get_cases_from_network_directory(p, prisonerOrm.cases_list)
    else:
        active_cases, cases = get_cases_from_network_directory(p, None)
    active_cases = identify_new_active_cases(active_cases, cases, filter_list)
    #  check if any cases in the active cases list are found in p.paid_cases_list ecf_case_num and remove them from the active cases list
    active_cases = filter_paid_cases(active_cases, prisonerOrm)

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


def filter_paid_cases(active_cases, prisonerOrm):
    if prisonerOrm:
        if prisonerOrm.paid_cases:
            for case in prisonerOrm.paid_cases:
                if case.ecf_case_num in active_cases:
                    active_cases.remove(case.ecf_case_num)
    return active_cases


def identify_new_active_cases(active_cases, cases, filter_list):
    for case in cases:
        if any(s in case for s in filter_list):
            active_cases.remove(case)
    active_cases.sort()
    return active_cases


def get_cases_from_network_directory(p, current_active_cases):
    cases = [f.name for f in os.scandir(p.case_search_dir) if f.is_dir()]
    active_cases = cases[:]
    if current_active_cases:
        for case in current_active_cases:
            if case.ecf_case_num in active_cases:
                active_cases.remove(case.ecf_case_num)
    return active_cases, cases


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
    if case.balance.amount_owed <= 0:
        case.case_comment = 'PAID'
    return case
