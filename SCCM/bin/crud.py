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



