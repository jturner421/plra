import os

import SCCM.bin.dataframe_cleanup as dc
import SCCM.models.case_schema as cs

filter_list = dc.populate_cases_filter_list()


def get_prisoner_case_numbers(p):
    """
    Identifies active cases for prisoner

    :return: oldest active case
    """
    print(f'Getting existing cases for {p.check_name}')

    cases = [f.name for f in os.scandir(p.case_search_dir) if f.is_dir()]
    active_cases = cases[:]
    for case in cases:
        if any(s in case for s in filter_list):
            active_cases.remove(case)
    active_cases.sort()
    for c in active_cases:
        p.cases_list.append(cs.CaseCreate(
            ecf_case_num=str.upper(c),
            comment='ACTIVE')
        )
    return p

def _format_name(self):
    # TODO - Need to finish this for Excel Output
    name = self.lookup_name.split()
    reordered_name = []
    if len(name) == 3:
        reordered_name.append(name[2])
        reordered_name.append(name[1])
        reordered_name.append(name[0])
        self.lookup_name = " ".join(reordered_name)
