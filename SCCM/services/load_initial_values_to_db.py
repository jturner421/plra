"""
Populates database with lookup values used by the application
"""

from SCCM.models.case_filter import CaseFilter
from SCCM.services.db_session import DbSession
from SCCM.models.suffix import SuffixTable


def main():
    session = DbSession.factory()
    suffix_list = ('jr', 'sr', 'ii', 'iii', 'iv', 'v')
    filter_list = ('PAID', 'CLOSED', 'DISMISSED', 'LOOK AT THIS', 'look at this', 'OVP', '.PDF', '.pdf', 'Habeas',
                   "HABEAS", 'Transfer', '_aka', 'Initial Partial Only', 'Paids%', 'TERMINATED', 'WITHDREW')

    for s in suffix_list:
        suffix = SuffixTable(suffix_name=s)
        session.add(suffix)

    for f in filter_list:
        case_filter = CaseFilter(filter_text=f)
        session.add(case_filter)

    session.commit()


if __name__ == '__main__':
    main()
