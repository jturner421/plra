from pathlib import Path

from SCCM.data.db_session import DbSession


def main():
    init_db()


def init_db():
    # ToDO: Need to change this for production
    p = Path.cwd()
    db_file = p.parent / 'db' / 'wiw_plra-old.sqlite'
    DbSession.global_init(db_file)


if __name__ == '__main__':
    main()
