import datetime

import sqlalchemy as sa

from SCCM.data.modelbase import SqlAlchemyBase


class CaseFilter(SqlAlchemyBase):
    __tablename__ = 'case_filters'

    id = sa.Column(sa.INT, primary_key=True, autoincrement=True)
    created_date = sa.Column(sa.DateTime, default=datetime.datetime.now)
    filter_text = sa.Column(sa.String)

    def __repr__(self):
        return '<Case Filter {}>'.format(self.filter_text)
