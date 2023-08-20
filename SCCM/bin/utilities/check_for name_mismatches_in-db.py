"""
This utility checks for name mismatches between state check names and db names
"""

from pathlib import Path

from SCCM.config import config
from SCCM.services.db_session import DbSession
from SCCM.models.prisoners import Prisoner


def main():
    p = Path.cwd()
    config_file = p.parent.parent / 'config' / 'config.ini'
    configuration = config.initialize_config(str(config_file))
    prod_vars = config.get_prod_vars(configuration, 'PROD')
    prod_db_path = prod_vars['NETWORK_DB_BASE_DIR']
    db_file_name = prod_vars['DATABASE_SQLite']
    db_file = f'{prod_db_path}{db_file_name}'
    db_session = DbSession.global_init(db_file)

    result = db_session.query(Prisoner).filter(Prisoner.judgment_name != Prisoner.legal_name).all()
    # TODO: need method to compare results of query
    for r in result:
        pass

if __name__ == '__main__':
    main()