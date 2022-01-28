import os
import sqlite3


def progress(status, remaining, total):
    print('Backing up Database')
    print(f'Copied {total - remaining} of {total} pages...')


def prod_db_backup(original, destination):
    db_orig = sqlite3.connect(original)
    db_backup = sqlite3.connect(destination)
    with db_backup:
        db_orig.backup(db_backup, pages=1, progress=progress)
    db_backup.close()
    db_orig.close()


def prod_db_restore(db_file, destination, db_backup_path, db_backup_file_name):
    print('An errror processing this check has occured. \n')
    db_orig = sqlite3.connect(db_file)

    backup = f'{db_backup_path}{db_backup_file_name}_backup.db'
    db_backup = sqlite3.connect(backup)
    db_restore = sqlite3.connect(destination)

    # first make a backup of the current state
    with db_orig:
        db_orig.backup(db_backup, pages=1)
    # Delete the db file
    os.remove(db_file)

    # Copy the restore DB to the original file name
    db_orig = sqlite3.connect(db_file)
    print('Restoring database to previous state.\n')
    with db_restore:
        db_restore.backup(db_orig, pages=1)

    db_backup.close()
    db_orig.close()
    db_restore.close()