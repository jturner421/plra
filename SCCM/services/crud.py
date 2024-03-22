from typing import List

from sqlalchemy.orm import Session

from SCCM.models.court_cases import CourtCase
from SCCM.models.prisoners import Prisoner
from SCCM.schemas import prisoner_schema
from SCCM.models import prisoners
from SCCM.models import court_cases
from SCCM.models import case_transaction
from SCCM.schemas.case_schema import CaseModel
from SCCM.services.db_session import DbSession


def create_prisoner(prisoner: prisoner_schema.PrisonerCreate) -> Prisoner:
    db_prisoner = prisoners.Prisoner(
        doc_number=prisoner.doc_number,
        judgment_name=prisoner.judgment_name,
        legal_name=prisoner.legal_name,
        vendor_code=prisoner.vendor_code
    )
    return db_prisoner


def get_prisoner_with_active_case(doc_number: int, legal_name: str) -> Prisoner:
    print(f'Retrieving {legal_name} from the database.\n')
    db = DbSession.factory()
    result = db.query(prisoners.Prisoner).filter(prisoners.Prisoner.doc_number == doc_number).first()
    if result:
        result.paid_cases = [case for case in result.cases_list if case.case_comment == 'PAID']
        result.cases_list = [case for case in result.cases_list if case.case_comment == 'ACTIVE']
        db.close()
        return result
    else:
        return None


def add_cases_for_prisoner(db_prisoner: prisoners.Prisoner,
                           p: prisoner_schema.PrisonerCreate) -> prisoners.Prisoner:
    """
    Adds processed cases to prisoner database model

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


def update_case_balances(case: CaseModel, db_prisoner_list: List[Prisoner]):
    pris_index_loc = next(i for i, v in enumerate(db_prisoner_list) if v.id == case.prisoner_id)
    prisoner = db_prisoner_list[pris_index_loc]
    case_index_loc = next(i for i, v in enumerate(prisoner.cases_list) if v.id == case.id)
    case_db = prisoner.cases_list[case_index_loc]

    case_db.amount_collected = case.balance.amount_collected
    case_db.amount_owed = case.balance.amount_owed
    return case_db


def update_case_transactions(case: CaseModel, case_db: CourtCase):
    case_db.case_transactions.append(case_transaction.CaseTransaction(
        check_number=case.transaction.check_number,
        amount_paid=case.transaction.amount_paid
    ))
    return case_db

# def add_transactions_to_database(prisoner_list, db_prisoner_list: List[Prisoner]):
#     for p in prisoner_list:
#         if p.exists:
#             new_transactions = [case for case in p.cases_list if case.transaction]
#             for t in new_transactions:
#                 case_db = update_case_balances(t, db_prisoner_list)
#                 session.add(case_db)
#         else:
#             db_prisoner = create_prisoner(session, p)
#             db_prisoner = add_cases_for_prisoner(db_prisoner, p)
#             session.add(db_prisoner)
#     db.commit()
