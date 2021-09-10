import datetime
import sqlalchemy as sa
from sqlalchemy import orm

from SCCM.data.modelbase import SqlAlchemyBase



# each table needs to be represented by a class

class Prisoner(SqlAlchemyBase):
    __tablename__ = 'prisoners'

    # id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    doc_num = sa.Column(sa.INT, primary_key=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    judgment_name = sa.Column(sa.String, index=True)
    legal_name = sa.Column(sa.String, index=True)
    vendor_code = sa.Column(sa.String, nullable=True)

    def __repr__(self):
        return '<Doc Number {}>'.format(self.doc_num)



