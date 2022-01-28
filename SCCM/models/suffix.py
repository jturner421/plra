import datetime

import sqlalchemy as sa

from SCCM.models.modelbase import SqlAlchemyBase


class SuffixTable(SqlAlchemyBase):
    __tablename__ = 'suffix_table'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    updated_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    suffix_name = sa.Column(sa.String, nullable=False)

    def __repr__(self):
        return '<Suffix Name {}>'.format(self.suffix_name)
