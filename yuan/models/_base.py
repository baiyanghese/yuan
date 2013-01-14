# coding: utf-8

from flask.signals import Namespace
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery

__all__ = [
    'db', 'YuanQuery', 'SessionMixin', 'model_created', 'model_updated',
    'model_deleted',
]

signals = Namespace()
model_created = signals.signal('model-created')
model_updated = signals.signal('model-updated')
model_deleted = signals.signal('model-deleted')

db = SQLAlchemy()


class YuanQuery(BaseQuery):
    def filter_in(self, key, ids):
        ids = set(ids)
        if len(ids) == 0:
            return {}
        if len(ids) == 1:
            ident = ids.pop()
            rv = self.get(ident)
            if not rv:
                return {}
            return {ident: rv}
        items = self.filter(key.in_(ids))
        dct = {}
        for u in items:
            dct[u.id] = u
        return dct

    def as_list(self, *columns):
        columns = map(db.defer, columns)
        return self.options(map(db.defer, columns))


class SessionMixin(object):
    def save(self):
        if self.id:
            emitter = model_updated
        else:
            emitter = model_created
        db.session.add(self)
        db.session.commit()
        emitter.send(self, model=self)
        return self

    def delete(self):
        db.session.delete(self)
        model_deleted.send(self, model=self)
        db.session.commit()
        return self
