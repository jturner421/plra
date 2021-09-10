"""
Utility to delete prisoner and associated case records and transactions from the database.
"""

from pathlib import Path

import keyring
import requests

from config import config
from data.db_session import DbSession
from SCCM.config import config
from SCCM.data.case_balance import CaseBalance
from SCCM.data.case_filter import CaseFilter
from SCCM.data.court_cases import CourtCase
from SCCM.data.db_session import DbSession
from SCCM.data.prisoners import Prisoner

# noinspection DuplicatedCode
config_path = Path.cwd()
config_file = config_path.parent / 'config' / 'config.ini'
configuration = config.initialize_config(str(config_file))
prod_vars = config.get_prod_vars(configuration, 'PROD')
prod_db_path = prod_vars['NETWORK_DB_BASE_DIR']
db_file_name = prod_vars['DATABASE_SQLite']
db_file = f'{prod_db_path}{db_file_name}'
db_session = DbSession.global_init(db_file)
ccam_username = prod_vars['CCAM_USERNAME']
base_url = prod_vars['CCAM_API']
ccam_password = keyring.get_password("WIWCCA", ccam_username)
session = requests.Session()
session.auth = (ccam_username, ccam_password)
cert_path = prod_vars['CLIENT_CERT_PATH']
session.verify = cert_path

doc_num = input('Enter the DOC number for the prisoner you wish to delete from the database: ')
result = db_session.query(Prisoner).filter(Prisoner.doc_num == doc_num).first()

if result:
    print(f'Do you wish to delete prisoner {result.legal_name}, DOC Number {result.doc_num} with the following cases:')
    for k, v in enumerate(result.court_cases, start=1):
        print(f'{v}\n')

    confirm_response = 'EMPTY'
    while confirm_response not in ('y', 'n') and confirm_response:
        try:
            confirm_response = input('[Y]es/[N]o: ')
            confirm_response = confirm_response.lower().strip()
        except ValueError:
            print("Sorry, I didn't understand that.")
            continue
        if confirm_response == 'y':
            db_session.delete(result)
            db_session.commit()
            break
        elif confirm_response == 'n':
            print('Exiting the program')
            exit(1)
        elif confirm_response not in ('y', 'n') and confirm_response:
            print('This is not a valid response')
            continue
else:
    print(f'Prisoner DOC number {doc_num} was not found')
    exit(1)