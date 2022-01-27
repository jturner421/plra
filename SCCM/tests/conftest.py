import pytest
import sqlite3
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from SCCM.models.prisoner_schema import PrisonerCreate
from SCCM.models.case_schema import CaseCreate
from SCCM.models.balance import Balance
from SCCM.models.transaction_schema import TransactionCreate

cents = Decimal('0.01')


@pytest.fixture
def setup_db():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()

    suffix_table_sql = """ CREATE TABLE IF NOT EXISTS suffix_table(
                            id integer not null
                            constraint suffix_table_pk
                            primary key autoincrement,
                            suffix_name  varchar not null
                    );"""

    cursor.execute(suffix_table_sql)
    suffix_list = [(None, 'jr'), (None, 'sr'), (None, 'ii'), (None, 'iii'), (None, 'iv'), (None, 'v')]
    cursor.executemany("Insert into suffix_table VALUES (?,?)", suffix_list)
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture
def setup_prisoner():
    items = {"doc_num": 15483,
             "check_name": 'Nate A Lindell',
             "amount_paid": Decimal(846.37).quantize(cents, ROUND_HALF_UP),
             "judgment_name": 'LINDELL, Nate'
             }
    p = PrisonerCreate(**items)
    p.cases_list.append(CaseCreate(
        ecf_case_num='06-CV-608',
        comment='ACTIVE',
        acct_cd='WIWAPCCA2659',
        ccam_case_num='DWIW306CV000608-001',
        balance=Balance(amount_assessed=805, amount_collected=91.28, amount_owed=713.72)
    ))
    p.cases_list.append(CaseCreate(
        ecf_case_num='07-CV-484',
        comment='ACTIVE',
        acct_cd='WIWAPCCA2659',
        ccam_case_num='DWIW307CV000484-001',
        balance=Balance(amount_assessed=350, amount_collected=1.50, amount_owed=348.50)
    ))

    p.cases_list.append(CaseCreate(
        ecf_case_num='12-CV-646',
        comment='ACTIVE',
        acct_cd='WIWAPCCA2659',
        ccam_case_num='DWIW312CV000646-001',
        balance=Balance(amount_assessed=855, amount_collected=0, amount_owed=855)
    ))
    return p


@pytest.fixture
def setup_prisoner_refund():
    items = {"doc_num": 15483,
             "check_name": 'Walter W Blanck',
             "amount_paid": Decimal(528.87).quantize(cents, ROUND_HALF_UP),
             "judgment_name": 'BLANCK, Walter',
             "refund": Decimal(528.87).quantize(cents, ROUND_HALF_UP)
             }
    p = PrisonerCreate(**items)
    p.overpayment = {'overpayment': True,
                     'ccam_case_num': 'DWIW314CV000135-001',
                     'assessed': 350,
                     'collected': 350,
                     'outstanding': 0,
                     'transaction amount': -528.87
                     }
    p.cases_list.append(CaseCreate(
        ecf_case_num='13-CV-193',
        comment='PAID',
        acct_cd='WIWAPCCA2659',
        ccam_case_num='DWIW313CV000193-001',
        balance=Balance(amount_assessed=350, amount_collected=350, amount_owed=0)
    ))
    p.cases_list.append(CaseCreate(
        ecf_case_num='14-CV-135',
        comment='PAID',
        acct_cd='WIWAPCCA2659',
        ccam_case_num='DWIW313CV000135-001',
        balance=Balance(amount_assessed=350, amount_collected=350, amount_owed=0)
    ))

    return p

@pytest.fixture
def prisoner_no_refund(setup_prisoner):
    pass