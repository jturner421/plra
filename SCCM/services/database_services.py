import os
import sqlite3
from SCCM.bin import get_files as gf
from datetime import datetime
from pathlib import Path


def progress(status, remaining, total):
    print(f'Copied {total - remaining} of {total} pages...')


def prod_db_backup(original, destination):
    db_orig = sqlite3.connect(original)
    db_backup = sqlite3.connect(destination)
    with db_backup:
        db_orig.backup(db_backup, pages=1, progress=progress)
    db_backup.close()
    db_orig.close()


def prod_db_restore(db_file, backup_directory):
    """
    Function to restore a database from a backup file from a specific check.
    :param db_file: Production Database file and path
    :param backup_directory: Directory where backups are stored
    :return: None
    """
    print('Restoring Backup of Database. \n')
    db_orig = sqlite3.connect(db_file)

    # Backup database for a specific check
    db_check_backup = sqlite3.connect(gf.choose_files_for_import()[0])

    # File name for backup of the original database.  Append today's date to the file name.
    original_db_backup_file_name = db_file.parts[-1] + "_" + datetime.strftime(datetime.today(), '%Y%m%d')
    original_backup_path = Path(backup_directory) / original_db_backup_file_name
    db_original_backup = sqlite3.connect(original_backup_path)

    # first make a backup of the current state
    with db_orig:
        print('Backing up current database')
        db_orig.backup(db_original_backup, pages=1, progress=progress)
    # Delete the db file
    os.remove(db_file)

    # recreate the db file
    db_orig = sqlite3.connect(db_file)

    # Copy the restore DB to the original file name
    print('Restoring database from check backup.\n')
    with db_check_backup:
        db_check_backup.backup(db_orig, pages=1, progress=progress)
    db_orig.close()
    db_check_backup.close()
    print('Restore Completed.\n')