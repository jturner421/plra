from sqlalchemy.orm import Session

from SCCM.models import prisoner_schema
from SCCM.data import prisoners


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



# def create_case_db_object(self, db_session, doc_number) -> DbSession:
#     db_session.add(CourtCase(prisoner_doc_num=doc_number,
#                              acct_cd=self.acct_cd,
#                              ecf_case_num=self.ecf_case_num,
#                              ccam_case_num=self.ccam_case_num,
#                              case_comment=self.status,
#                              amount_assessed=Decimal(self.balance.amount_assessed).quantize(cents,
#                                                                                             ROUND_HALF_UP),
#                              amount_collected=Decimal(self.balance.amount_collected).quantize(cents,
#                                                                                               ROUND_HALF_UP),
#                              amount_owed=Decimal(self.balance.amount_owed).quantize(cents,
#                                                                                     ROUND_HALF_UP)
#                              ))
#     return db_session

