"""
This module is used to convert the output from screen scraping the WI DOC site to obtain prisoner DOC numbers and
aliases
"""

import pandas as pd


def convert_csv_to_dataframe(file):
    """
    Reads in prisoner csv file and ensures that DOC number is not converted to a Float. Uses the court network name
    as the index.
    :param file: path to csv
    :return: Dataframe of prisoner data
    """
    df = pd.read_csv(file, sep=',', header=None, dtype={2: 'str'})
    # df.rename(index={0: 'prisoner_name'})
    df.rename(columns={0: 'prisoner_name',1: 'case_list', 2: 'doc_number', 3: 'state_name', 4: 'status', 5: 'aliases'},
              inplace=True)
    return df


def current_prisoners(df):
    """
    Drop prisoners not found in WI DOC lookup by checking the status column for found and filtering out not found rows
    Found_prisoners is a boolean variable with True or False used as a filter

    :param df: Dataframe of all prisoners
    :return: Dataframe of active prisoners
    """
    found_prisoners = df['status'] == 'Found'
    act_prisoners = df[found_prisoners]
    return act_prisoners


def in_active_prisoners(df):
    """
    Identify prisoners not found in WI DOC lookup by checking the status column for found and filtering out found rows
    not_found_prisoners is a boolean variable with True or False used as a filter

    :param df: Dataframe of all prisoners
    :return: Dataframe of inactive prisoners
    """

    not_found_prisoners = df['status'] == 'Not Found'
    inact_prisoners = df[not_found_prisoners]
    return inact_prisoners


def mult_name_match(df):
    """
    Identify active prisoners that produced multiple matches WI DOC lookup.
    multiple is a boolean variable with True or False used as a filter

    :param df: Dataframe of all active prisoners
    :return: Dataframe of prisoners with multiple name matches
    """

    mulitple = df['doc_number'].isnull()
    multiple_name_matches = df[mulitple]
    return multiple_name_matches


def main():
    file_to_read = 'prisoners.txt'
    prisoner_data = convert_csv_to_dataframe(file_to_read)

    # Begin separating data to process efficiently
    active_prisoners = current_prisoners(prisoner_data)
    inactive_prisoners = in_active_prisoners(prisoner_data)

    # Isolate active prisoners where a name match at WI DOD produced a single result
    single_cases_for_prisoner = active_prisoners.dropna()
    print(single_cases_for_prisoner.info())
    print(single_cases_for_prisoner.head())
    multiple_matches_for_prisoner = mult_name_match(active_prisoners)
    print(multiple_matches_for_prisoner.info())
    print(multiple_matches_for_prisoner.head())


if __name__ == '__main__':
    main()
