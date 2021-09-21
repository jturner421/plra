import os
from collections import Counter
from decimal import Decimal
from typing import Optional

import fuzz as fuzz
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from SCCM.bin import ccam_lookup as ccam
from SCCM.bin import convert_to_excel as cte
from SCCM.data.case_balance import CaseBalance
from SCCM.data.case_transaction import CaseTransaction
from SCCM.data.court_cases import CourtCase
from SCCM.data.prisoners import Prisoner


class Prisoners:
    """
    A class used to represent a Payee

    Attributes
    ----------
    check_name : str
        the name of the payee listed on the state check
    doc_num : str
        payee Department of Corrections number
    amount : Decimal
        amount paid on check
    lookup_name : str
        payee name listed on the state check
    orig_case_number : str
        case number stored on network share
    plra_name : str
        prisoner name stored on network share
    search_dir : str
        path to base directory on network share to match payee to prisoner
    case_search_dir : str:
        path to directory on network share to retrieve prisoner case information
    formatted_case_num: str
        oldest active case number formatted for CCAM
    ccam balance : list
        aggregate account balance for prisoner retrieved from CCAM
    overpayment : bool
        flag if overpayment exists

    Methods
    ----------
    drop_suffix_from_name (suffix_list)
        Strips suffix from name to prepare for string matching algorithm

    construct_search_directory_for_prisoner (base_dir)
        Creates path to base directory on network share to match payee to prisoner

    get_name_ratio
        Determines closest matching strings of prisoner names

    create_prisoner(db_session, session, base_url)
        Creates new prisoner record in database

    get_prisoner_case_numbers(filter_list)
        Identifies active cases for selected prisoner

    create_transaction(result, check_number,db_session)
        Records prisoner payment in database

    update_account_balance(result, db_session)
         Updates case balance for prisoner and checks if case is paid off

    update_pty_acct_cd(result, session)
        Updates JIFMS account code for prisoner if not found
    """

    def __init__(self, check_name, doc_num, amount_paid):
        self.check_name = check_name
        self.doc_num = doc_num
        self.amount_paid = amount_paid
        # self.lookup_name = None
        self.cases_list = []
        # self.orig_case_number = None
        # self.plra_name = None
        # self.search_dir = None
        # self.case_search_dir = None
        # self.formatted_case_num = None
        # self.ccam_balance = None
        # self.acct_cd = None
        self.pty_cd: Optional[str] = None
        # self.overpayment = None

    def __repr__(self):
        return (f'{self.__class__.__name__}'
                f'('f'{self.check_name!r}, {self.doc_num!r})')

    def __str__(self):
        return f'{self.check_name} with an Agency Tracking ID of {self.doc_num}'

    def drop_suffix_from_name(self, suffix_list):
        """
        Strips suffix from name to prepare for string matching algorithm

        :type suffix_list: Tuple[str, str, str, str, str, str]
        :param suffix_list: List of suffix names
        """
        lookup_name = self.check_name
        lookup_name = lookup_name.lower()
        name = str.split(lookup_name, ' ')
        pull_suffix = set(name).intersection(suffix_list)
        if pull_suffix:
            for item in pull_suffix:
                name.remove(item)
        name = ' '.join(name).title()
        self.lookup_name = name
        return self

    def construct_search_directory_for_prisoner(self, base_dir):
        """
        Creates path to base directory on network share to match payee to prisoner.
        Format is base_dir plus first initial of last name.

        Example : '/Volumes/DC/Groups/Finance/Trust Fund/Case Files/J'
        :param base_dir: base directory location for electronic case files specified in config.ini
        :return: search directory for input to name matching algorithm
        """
        last_name = self.lookup_name.split(" ")

        # Check for hyphenation and handle
        if '-' in last_name[len(last_name) - 1]:
            split_last_name = str.split(last_name[len(last_name) - 1], '-')
            last_name = split_last_name[0]
            last_initial = last_name[0].upper()
        else:
            last_initial = last_name[-1][0].upper()

        search_path = os.path.join(base_dir, last_initial)
        return search_path

    def __name_token_sort_ratio(self, directory_name):
        token_sort_dict = Counter({})
        lookup_name = self.lookup_name
        for name in directory_name:
            directory_name = name[0]
            token_sort_ratio = fuzz.token_sort_ratio(name, lookup_name)
            d = {name[0]: token_sort_ratio}
            token_sort_dict.update(d)
        return token_sort_dict

    def get_name_ratio(self):
        """
        Determines closest matching strings to check name from a list of prisoner names using Levenshtein Distance.
        Method combines Process and Token Set Ratio score to improve accuracy

        :return: prisoner name matching payee name
        """
        directory = os.listdir(self.search_dir)
        ratio_names = process.extract(self.lookup_name, directory)
        highest = process.extractOne(self.lookup_name, directory)
        # Handling edge cases and validate highest match
        # get token sort ratios for top three directory matches
        token_sort_ratios = Prisoners.__name_token_sort_ratio(self, ratio_names)

        ratio_dicts = Counter(dict(ratio_names))
        # combine dictionary to generate score
        search_score = token_sort_ratios + ratio_dicts
        max_value = max(search_score.values())
        highest_value_name = [k for k, v in search_score.items() if v == max_value]
        return highest_value_name[0]

    def _get_cases_from_network(self):
        cases = os.listdir(self.case_search_dir)
        self.cases_list = cases

    def _insert_ccam_account_balances(self, db_session, new_payee, i, session, base_url):
        # TODO move to case balance class
        """db_session, new_payee, case_pos, session, base_url
        Inserts JIFMS CCAM balances for current payee and identified case
        :param db_session: SQLAlchemy session
        :param new_payee: Person object
        :param i:
        :param session: Requests session for API lookup
        :param base_url:Base url used to construct API call

        """
        # get DB session
        formatted_case_number = cte.format_case_num(self.orig_case_number)
        # get case balances from JIFMS
        self.ccam_balance = ccam.get_ccam_account_information(formatted_case_number, session, base_url)
        payments = self.ccam_balance
        if payments["data"]:
            new_payee.court_cases[i].acct_cd = payments['data'][0]['acct_cd']
            ccam.sum_account_balances(payments, self)
            # populate balances for cases in person object
            balances = [self.ccam_balance["Total Owed"], self.ccam_balance["Total Collected"],
                        self.ccam_balance["Total Outstanding"]]
            new_payee.court_cases[i].case_balance.append(CaseBalance(amount_assessed=balances[0],
                                                                     amount_collected=balances[1],
                                                                     amount_owed=balances[2]))

            if new_payee.court_cases[i].case_balance[0].amount_owed > 0:
                new_payee.court_cases[i].case_comment = 'ACTIVE'
            else:
                new_payee.court_cases[i].case_comment = "PAID"

            db_session.add(new_payee)
        else:
            new_payee.court_cases[i].case_comment = "PAID"
            new_payee.court_cases[i].case_balance.append(CaseBalance(amount_assessed=0,
                                                                     amount_collected=0,
                                                                     amount_owed=0))
            db_session.add(new_payee)

    # noinspection PyUnresolvedReferences
    def create_prisoner(self, db_session, session, base_url):
        """
        Creates new prisoner record in database
        :param db_session: SQLAlchemy session
        :param session: Requests session for API lookup
        :param base_url: Base url used to construct API call
        """
        print(f'Creating new prisoner record for {self.lookup_name}\n')
        new_payee = Prisoner(doc_num=self.doc_num, judgment_name=self.plra_name, legal_name=self.lookup_name)
        case_pos = 0

        for c in self.cases_list:
            new_payee.court_cases.append(CourtCase(case_num=c))
            self.orig_case_number = c
            Prisoners._insert_ccam_account_balances(self, db_session, new_payee, case_pos, session, base_url)
            case_pos += 1

    def get_prisoner_case_numbers(self, filter_list):
        """
        Identifies active cases for prisoner
        :param filter_list: list of cases for a prisoner
        :return: oldest active case
        """
        from SCCM.bin.case import Case
        cases = [f.name for f in os.scandir(self.case_search_dir) if f.is_dir()]
        active_cases = cases[:]
        for case in cases:
            if any(s in case for s in filter_list):
                active_cases.remove(case)
        active_cases.sort()
        for c in active_cases:
            self.cases_list.append(Case(c, 'ACTIVE', overpayment=False))
        # return active_cases

    def _format_name(self):
        # TODO - Need to finish this for Excel Output
        name = self.lookup_name.split()
        reordered_name = []
        if len(name) == 3:
            reordered_name.append(name[2])
            reordered_name.append(name[1])
            reordered_name.append(name[0])
            self.lookup_name = " ".join(reordered_name)

    def create_transaction(self, check_number, db_session):
        """
        Records prisoner payment in database
        :param result: Case information for selected prisoner
        :param check_number: Check number for payment made
        :param db_session: SQLAlchemy session
        :return:
        """
        print(f'Creating transaction for {self.check_name}')

        self.current_case.case_transactions.append(
            CaseTransaction(court_case_id=self.current_case.id, check_number=check_number, amount_paid=self.amount))
        # db_session.add(self.current_case)
        # db_session.commit()

    def update_account_balance(self):
        """
        Updates case balance for prisoner, checks if case is paid off, and adds to database session for
        update
        :param result: Case information for selected prisoner
        :param db_session: SQLAlchemy session
        """

        print(f'Updating case balances for {self.check_name}')

        self.current_case.case_balance[0].amount_owed = self.current_case.case_balance[0].amount_owed - self.amount

        if self.current_case.case_balance[0].amount_owed <= 0:
            self.current_case.case_balance[0].amount_owed = 0
            self.current_case.case_comment = 'PAID'
            self.current_case.case_balance[0].amount_collected = self.current_case.case_balance[0].amount_assessed
            return

        self.current_case.case_balance[0].amount_collected = self.current_case.case_balance[
                                                                 0].amount_collected + self.amount
        if self.current_case.case_balance[0].amount_collected > self.current_case.case_balance[0].amount_assessed:
            self.current_case.case_balance[0].amount_collected = self.current_case.case_balance[0].amount_assessed

    def update_pty_acct_cd(self, result, session):
        """
        Updates JIFMS account code for prisoner if not found
        :param result: Case information for selected prisoner
        :param session:
        :return: SQLAlchemy session
        """
        update_values = {'acct_code': self.acct_cd, 'vendor_code': self.pty_cd}
        for key, value in update_values.items():
            if key == 'acct_code':
                result[0].CourtCase.acct_cd = value
            else:
                setattr(result[0].CourtCase.prisoner, key, value)
        session.commit()
