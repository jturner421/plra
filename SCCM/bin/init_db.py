"""
Creates global SQLAlchemy session.
"""
from pathlib import Path

from SCCM.data.db_session import DbSession


def main():
    p = Path.cwd()
    db_file = p.parent / 'db' / 'wiw_plra-old.sqlite'
    DbSession.global_init(str(db_file))


if __name__ == '__main__':
    main()