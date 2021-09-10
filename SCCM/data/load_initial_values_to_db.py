"""
Populates database with lookup values used by the application
"""
from pathlib import Path

from SCCM.data.case_filter import CaseFilter
from SCCM.data.db_session import DbSession
from SCCM.data.suffix import SuffixTable


def init_db():
    # p = Path.cwd()
    # db_file = p.parent / 'db' / 'wiw_plra-old.sqlite'
    db_file = '/Users/jwt/wiw_plra.sqlite'
    DbSession.global_init(str(db_file))


def main():
    suffix_list = ('jr', 'sr', 'ii', 'iii', 'iv', 'v')
    filter_list = ('PAID', 'CLOSED', 'DISMISSED', 'LOOK AT THIS', 'look at this', 'OVP', '.PDF', '.pdf', 'Habeas',
                   "HABEAS", 'Transfer', '_aka', 'Initial Partial Only', 'Paids%', 'TERMINATED')
    init_db()
    session = DbSession.factory()
    s = session

    for s in suffix_list:
        suffix = SuffixTable(suffix_name=s)
        session.add(suffix)

    for f in filter_list:
        filter = CaseFilter(filter_text=f)
        session.add(filter)

    session.commit()


if __name__ == '__main__':
    main()
