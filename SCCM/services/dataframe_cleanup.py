from SCCM.models.case_filter import CaseFilter
from SCCM.models.suffix import SuffixTable
from SCCM.services.db_session import DbSession
from sqlalchemy import select


def populate_suffix_list():
    """
    Retrieves a list of popular suffix

    :return: A list of strings to check against names that contain a suffix
    """
    s = DbSession.factory()
    stmt = select(SuffixTable.suffix_name)
    suffix_query = s.execute(stmt).all()
    suffix_list = [s[00] for s in suffix_query]
    return suffix_list


def populate_cases_filter_list():
    """
    Retrieves a list of of strings from default DB
    :return: a list of strings used to filter against inactive case numbers
    """
    s = DbSession.factory()
    stmt = select(CaseFilter.filter_text)
    filter_query = s.execute(stmt).all()
    case_filter = []
    for f in filter_query:
        case_filter.append(f[0])
    case_filter_list = tuple(case_filter)
    return case_filter_list


def aggregate_prisoner_payment_amounts(dframe):
    """
    Totals paid amounts per payee to apply to oldest active case

    :param dframe: Dateframe from state check detail
    :return: Dataframe with aggregate amounts
    """
    # Get clean list of names with associated DOC #
    dframe = dframe.reset_index(drop=True)
    df_names = dframe
    df_names = df_names.drop('Amount', axis=1)
    df_names = df_names.drop_duplicates()

    # Get aggregate sum of payments indexed by DOC#
    dframe_sum = dframe.groupby('DOC', as_index=False).agg({'Amount': 'sum'})

    # Merge results
    results = df_names.merge(dframe_sum)
    return results
