import argparse
from pathlib import Path

from SCCM.config.config_model import PLRASettings
from SCCM.services import database_services


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Enter mode [dev,test,prod] for execution")
    args = parser.parse_args()

    if args.mode == 'dev':
        config_file = '../../config/dev.env'
        settings = PLRASettings(_env_file=config_file, _env_file_encoding='utf-8')

    db_file = Path(settings.db_base_directory) / settings.db_file

    database_services.prod_db_restore(db_file, settings.db_backup_directory)


if __name__ == '__main__':
    main()
