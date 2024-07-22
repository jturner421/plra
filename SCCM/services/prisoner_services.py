import os
from collections import Counter

import fuzz as fuzz
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import SCCM.services.dataframe_cleanup as dc
import SCCM.schemas.prisoner_schema as pris_schema

suffix_list = dc.populate_suffix_list()


def add_prisoner_to_db_session(network_base_dir: str, p: pris_schema.PrisonerCreate):
    print(f'{p.legal_name} found in database. Adding to session.... ')
    # Get parameters, create new user, insert into DB and load balances
    # search for name on network share
    p.legal_name = drop_suffix_from_name(p.legal_name)
    p.search_dir = construct_search_directory_for_prisoner(p.legal_name, network_base_dir)
    p.judgment_name = get_name_ratio(p)
    p.case_search_dir = f"{p.search_dir}/{p.judgment_name}"
    return p


def drop_suffix_from_name(check_name: str) -> str:
    """
    Strips suffix from name to prepare for string matching algorithm

    """
    lookup_name = check_name
    lookup_name = lookup_name.lower()
    name = str.split(lookup_name, ' ')
    pull_suffix = set(name).intersection(suffix_list)
    if pull_suffix:
        for item in pull_suffix:
            name.remove(item)
    name = ' '.join(name).title()
    return name


def construct_search_directory_for_prisoner(lookup_name: str, base_dir: str):
    """
    Creates path to base directory on network share to match payee to prisoner.
    Format is base_dir plus first initial of last name.
    Example : '/Volumes/DC/Groups/Finance/Trust Fund/CaseBase Files/J'

    :param lookup_name: name of payee to match to prisoner
    :param base_dir: base directory location for electronic case files specified in config.ini
    :return: search directory for input to name matching algorithm
    """
    last_name = lookup_name.split(" ")

    # Check for hyphenation and handle
    if '-' in last_name[len(last_name) - 1]:
        split_last_name = str.split(last_name[len(last_name) - 1], '-')
        last_name = split_last_name[0]
        last_initial = last_name[0].upper()
    else:
        last_initial = last_name[-1][0].upper()

    search_path = os.path.join(base_dir, last_initial)
    return search_path


def __name_token_sort_ratio(p, directory_name):
    token_sort_dict = Counter({})
    lookup_name = p.legal_name
    for name in directory_name:
        # directory_name = name[0]
        token_sort_ratio = fuzz.token_sort_ratio(name, lookup_name)
        d = {name[0]: token_sort_ratio}
        token_sort_dict.update(d)
    return token_sort_dict


def get_name_ratio(p):
    """
    Determines closest matching strings to check name from a list of prisoner names using Levenshtein Distance.
    Method combines Process and Token Set Ratio score to improve accuracy

    :return: prisoner name matching payee name
    """
    directory = os.listdir(p.search_dir)
    ratio_names = process.extract(p.legal_name, directory)
    highest = process.extractOne(p.legal_name, directory)
    # Handling edge cases and validate the highest match
    # get token sort ratios for top three directory matches
    token_sort_ratios = __name_token_sort_ratio(p, ratio_names)

    ratio_dicts = Counter(dict(ratio_names))
    # combine dictionary to generate score
    search_score = token_sort_ratios + ratio_dicts
    max_value = max(search_score.values())
    highest_value_name = [k for k, v in search_score.items() if v == max_value]
    return highest_value_name[0]
