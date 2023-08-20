# State Check Conversion to CCAM (SCCC)

SCCC is a CLI (Command Line Interface) application that takes prisoner PLRA payments collected by the Wisconsin Department 
of Corrections in accordance with the PLRA Act and creates a formatted Excel file for upload to JIFMS CCAM.  The application takes 
a PDF of the state check detail, performs data cleanup and validation, retrieves the oldest active case, updates case balance 
information in its internal database, and keeps a record of transaction history. 

While JIFMS CCAM remains the official repository for PLRA payments, SCCC provides real-time account balances and transaction history to aid in overpayment identification 
and case research by pro se staff and chambers.
      
## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 
See deployment for notes on how to deploy the project on a live system.

### Prerequisites
It's assumed that you have Git and SQLite available on your system. If not, please follow the instructions available at [the Git home page](https://git-scm.com) and [SQLite binaries](https://www.sqlite.org/download.html)
for your operating system.

The application was developed using Python 3.7.2.  It's necessary to install or update to Python 3.7 or later.

This project uses [Keyring](https://pypi.org/project/keyring/) to store secrets. 
Keyring uses the macOS [Keychain](https://en.wikipedia.org/wiki/Keychain_%28software%29) or 
[Windows Credential Locker](https://docs.microsoft.com/en-us/windows/uwp/security/credential-locker) as a repository. 

This project also uses the following third-party modules:
* [Pandas](https://pandas.pydata.org/)
* [NumPy](https://www.numpy.org/)
* [Camelot-py](https://camelot-py.readthedocs.io/en/master/user/install.html#install). Camelot-py's dependencies include
 [Tkinter](https://wiki.python.org/moin/TkInter) and [ghostscript](https://www.ghostscript.com/) which need to be installed separately.
* [Fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy)
* [Python-levenshtien](https://github.com/ztane/python-Levenshtein)
* [SQLAlchemy](https://www.sqlalchemy.org)
* [Alembic](https://alembic.sqlalchemy.org/en/latest/)
* [Pytest](https://docs.pytest.org/en/latest/) 
* [Openpyxl](https://pypi.org/project/openpyxl/)
 
Python packages necessary to run the application are automatically loaded by their respective modules.  Instructions for downloading required 
packages can be found in the Installing section of this readme. 
### Installing
#### Packages and Dependencies
Packages and dependencies are managed through Pipenv.  To install Pipenv run:
```
$ pip3 install pipenv
```
In the directory where you plan to store the project source, we will create a virtual environment to isolate development:
```
$ pipenv shell
```  
Clone the project repository:
```
$ git clone https://cfsr.sso.dcn/WIWD/mail_log.git
```
Install project dependencies:
```
pipenv install Pipfile
```

#### Appplication Secrets
Follow the instructions for your operating system to load login credentials (e.g. JIFMS API) into Keyring.

#### Database Installation and Database Migration Managament
To initialize the SQLlite database, change to the project directory root and run in the following order:
```
python ./SCCM/bin/init_db.py # çreates DB from ORM model
python ./SCCM/bin/load_initial_values_to_db.py # load filter values
```
The application uses Alembic to manage database migrations for development and production by interfacing with the SQLalchemy model metatdata. 
The structure of this environment, including generated migration scripts, looks like:

yourproject/\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;alembic/\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;env.py\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;README\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;script.py.mako\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;versions/\
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;82e0810c5d42_added_reconciliation_table.py

Each revision to the database is documented in a migration script located in the versions subdirectory. 

Since Alembic is not managed through by the SQLAlchemy orm, we need to recreate the database manually table to ensure that future migrations run properly. Do not initilize Alembic as described in their documentation as you will overwrite 
key configuration information located in alembic.ini and env.py.

If your IDE does not provide a method for loading .sql files (Pycharm Professional makes this a trivial task) drop to the command line and run:
```
sqlite3 ./SCCM/db/wiw_plra.sqlite # open the database
sqlite> .read ./SCCM/wi_doc_data/data_exports/main_alembic_version.sql
```

#### Loading Seed Data
SQL data files are provided to seed the database for development.  The files are located in the ./SCCM/wi_doc_data/data_exports directory
and provide data for the following tables:

* prisoners
* court_cases
* case_balance

While you are still in the SQLite environment environment, load the seed data:
```
sqlite> .read ./SCCM/wi_doc_data/data_exports/main_prisoners.sql
sqlite> .read ./SCCM/wi_doc_data/data_exports/main_court_cases.sql.sql
sqlite> .read ./SCCM/wi_doc_data/data_exports/main_case_balance.sql.sql
sqlite> .exit # exit session
``` 

#### Checking Your Database Revision
Check you version of the database:
```
(mail_log) Joels-MacBook-Pro:mail_log jwt$ alembic current
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
82e0810c5d42 (head)
``` 
Check the head revision number provided at the command line against versions located in /alembic/versions

To upgrade the database to the latest revision if necessary:
```
(mail_log) Joels-MacBook-Pro:mail_log jwt$ alembic upgrade head
```
Sample output of a migration:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 82e0810c5d42, Added reconciliation table
```
View all history:
```
(mail_log) Joels-MacBook-Pro:mail_log jwt$ alembic history
<base> -> 82e0810c5d42 (head), Added reconciliation table
```
See the Alembic documentation for instructions on creating additional database migrations.

#### Database Backups
Due to the program workflow and the unit of work pattern that SQLAlchemy uses for transaction processing, any error while processing a state check could lead to incorrect
case balances or orphaned records should a program error occur that has not been anticipated. Program execution will also exit in the event the aggregate total of the check statement
does not match the total processed by the application. 

To allow for recovery, prior to the first inserted record, the application will make a backup copy 
of the SQLite database to the db backup path with the following naming convention: number_processed date.sqlite.

#### Database Schema

[Image of database schema](SCCM/db/wiw_plra_schema.png)
#### Application Configuration
Confiiguration data is managed by [configparser](https://docs.python.org/3.7/library/configparser.html) using a style similar to what is found in a Microsoft Windows INI file.
SCCC parameters should be configured in /SCCM/config/config.ini. An annotated template file, config.ini_template is provided to use for developing a local config.ini file.

### Running the Application

To run the application simply enter from a command line:
```
python state_check_convert.py 

```
The application will prompt the user to choose one or more PDF files to process and perform at a high-level the following actions on each file:

*  Convert the PDF into a Panda Dataframe
*  Aggregate multiple payments per prisoner into one payment
*  Match DOC number from PDF to DOC number in the application database
*  If no match is found, the application will retrieve case information from the network share, query JIMS CCAM through an API call, and update case balances
*  Retrieve transaction history for the oldest active case
*  Identify any overpayments
*  Update case balances with prisoner payment and record a transaction
*  Populate a Microsoft Excel file to serve as an input to a JIFMS batch upload job to create receipts

### Performing a Reconciliation between JIFMS and the Application Database

Two scripts: [reconcile_JIMS_to_db_for_all_prisoners.py](SCCM/bin/reconciliation/reconcile_db_to_CCAM_for_all_prisoners.py) and [update_db_balances_from_JIFMS_for_all_prisoners.py](SCCM/bin/reconciliation/update_db_balances_from_JIFMS_for_all_prisoners.py) are provided to reconcile balances between JIFMS and the application database. They can found in [SCCM/bin/reconciliation](SCCM/bin/reconciliation)
Typically, a reconciliation should be run prior to processing new state checks provided that all outstanding uploads to JIFMS have been completed and posted. If this is not the case, running a reconciliation will hinder the 
ability of the application to identify and mark prisoner over payments and will likely result in false positives.

### Utilities

A set of command line utilities can be found in [SCCM/bin/utilities](SCCM/bin/utilities)

* API_single_case_lookup.py - Command line JIFMS case lookup. Uses API to retrieve case information and prints to screen.
* db_case_lookup.py - Command line database case lookup. Retrieves case information and prints to screen.
* delete_prisoner_from_database.py - Utility to delete prisoner and associated case records and transactions from the database.
 
### Known Issues/To Do

*  If a payment satisfies the outstanding balance for a case, the application will not automatically apply the remainder of the payment
to the next active case if it exists 
   
      
## Deployment

TBD

## Contributing

Please read [CONTRIBUTING.md] for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [Gitlab](https://cfsr.sso.dcn) for versioning. For the versions available, see the [tags on this repository](https://cfsr.sso.dcn/WIWD/mail_log.git). 

## Authors

* **Joel Turner** - [Western District of Wisconsin](https://intranet.wiwd.circ7.dcn/)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License




