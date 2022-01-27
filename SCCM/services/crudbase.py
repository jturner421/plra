from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy.orm import Session
from SCCM.models import prisoner_schema
from SCCM.data import prisoners
from SCCM.data import court_cases
from SCCM.data import case_transaction


class CRUDBase:
    def __init__(self, model):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get_prisoner(self, db: Session, doc_num: int):
        return db.query(self.model).filter(self.model.doc_num == doc_num).first()



