from typing import List

from sqlalchemy.orm import Session

from SCCM.data.prisoners import Prisoner
from SCCM.models import prisoner_schema
from SCCM.data import prisoners
from SCCM.data import court_cases
from SCCM.data import case_transaction
from SCCM.models.case_schema import CaseModel


def create_prisoner(db: Session, prisoner: prisoner_schema.PrisonerCreate):
    db_prisoner = prisoners.Prisoner(
        doc_num=prisoner.doc_num,
        judgment_name=prisoner.judgment_name,
        legal_name=prisoner.legal_name,
        vendor_code=prisoner.vendor_code
    )
    db.add(db_prisoner)
    db.flush()
    db.refresh(db_prisoner)
    return db_prisoner


def get_prisoner_with_active_case(db: Session, doc_num: int, legal_name: str):
    print(f'Retreiving {legal_name} from the database.\n')
    result = db.query(prisoners.Prisoner).filter(prisoners.Prisoner.doc_num == doc_num).first()
    if result:
        result.cases_list = [case for case in result.cases_list if case.case_comment == 'ACTIVE']
        return result
    else:
        return None


def add_cases_for_prisoner(db: Session, db_prisoner: prisoners.Prisoner,
                           p: prisoner_schema.PrisonerCreate) -> prisoners.Prisoner:
    """
    Adds processed cases to prisoner database model

    :param db: SQLAlchemy session
    :param db_prisoner: SqlAlchemy Data Model
    :param p: Pydantic Schema
    :return: prisoner database object
    """
    for case in p.cases_list:
        new_case = court_cases.CourtCase(
            prisoner_id=db_prisoner.id,
            acct_cd=case.acct_cd,
            ecf_case_num=case.ecf_case_num,
            ccam_case_num=case.ccam_case_num,
            case_comment=case.case_comment,
            amount_assessed=case.balance.amount_assessed,
            amount_collected=case.balance.amount_collected,
            amount_owed=case.balance.amount_owed
        )
        if case.transaction:
            transaction = case_transaction.CaseTransaction(
                check_number=case.transaction.check_number,
                amount_paid=p.amount_paid
            )
            new_case.case_transactions.append(transaction)
        # TODO - check for zero balance and marked PAID
        db_prisoner.cases_list.append(new_case)
    return db_prisoner


def _create_transaction(db: Session, db_prisoner: prisoners.Prisoner, p: prisoner_schema.PrisonerCreate):
    pass


def update_case_balances(db: Session, case: CaseModel, db_prisoner_list: List[Prisoner]):
    pris_index_loc = next(i for i, v in enumerate(db_prisoner_list) if v.id == case.prisoner_id)
    prisoner = db_prisoner_list[pris_index_loc]
    case_index_loc = next(i for i, v in enumerate(prisoner.cases_list) if v.id == case.id)
    case_db = prisoner.cases_list[case_index_loc]
    case_db.amount_collected = case.balance.amount_collected
    case_db.amount_owed = case.balance.amount_owed # TODO Check for zero balance and marked case paid
    case_db.case_transactions.append(case_transaction.CaseTransaction(
        check_number=case.transaction.check_number,
        amount_paid=case.transaction.amount_paid
    ))
