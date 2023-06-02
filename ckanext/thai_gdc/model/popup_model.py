import ckan.model as model
import sqlalchemy as sa
from sqlalchemy import String
from sqlalchemy.orm import class_mapper

try:
    from sqlalchemy.engine.result import RowProxy
except:
    from sqlalchemy.engine.base import RowProxy

types = sa.types

gdc_configs_table = sa.Table('gdc_configs', model.meta.metadata,
                             sa.Column('conf_key', String(100), primary_key=True, default=u''),
                             sa.Column('conf_value', types.UnicodeText, default=u''),
                             sa.Column('conf_group', String(50), default=u''),
                             )

model.meta.metadata.create_all()


class GdcConfigs(model.DomainObject):
    @classmethod
    def get(cls, conf_key):
        query = model.Session.query(cls).autoflush(False)
        return query.filter_by(conf_key=conf_key).first()

    @classmethod
    def get_group(cls, conf_group):
        query = model.Session.query(cls).autoflush(False)
        return query.filter_by(conf_group=conf_group)


model.meta.mapper(
    GdcConfigs,
    gdc_configs_table,
)
