from sqlalchemy.orm import Session

from SCCM.models import prisoner_schema
from SCCM.data import prisoners
from SCCM.data import court_cases
from SCCM.data import case_transaction


def create_prisoner(db: Session, prisoner: prisoner_schema.PrisonerCreate):
    db_prisoner = prisoners.Prisoner(
        doc_num=prisoner.doc_num,
        judgment_name=prisoner.judgment_name,
        legal_name=prisoner.check_name,
        vendor_code=prisoner.pty_code
    )
    db.add(db_prisoner)
    db.flush()
    db.refresh(db_prisoner)
    return db_prisoner


def add_cases_for_prisoner(db: Session, db_prisoner: prisoners.Prisoner, p: prisoner_schema.PrisonerCreate) -> prisoners.Prisoner:
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
            case_comment=case.comment,
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

        db_prisoner.cases.append(new_case)
    return db_prisoner


def _create_transaction(db: Session, db_prisoner: prisoners.Prisoner, p: prisoner_schema.PrisonerCreate):
    pass
