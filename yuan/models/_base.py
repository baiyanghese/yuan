# coding: utf-8

import datetime
from flask.signals import Namespace
from flask.ext.sqlalchemy import SQLAlchemy

__all__ = [
    'db', 'SessionMixin',
    'model_updated', 'model_deleted',
    'project_signal', 'package_signal'
]

signals = Namespace()
model_updated = signals.signal('model-updated')
model_deleted = signals.signal('model-deleted')
project_signal = signals.signal('project-signal')
package_signal = signals.signal('package-signal')

db = SQLAlchemy()


class SessionMixin(object):
    def to_dict(self, *columns):
        dct = {}
        for col in columns:
            value = getattr(self, col)
            if isinstance(value, datetime.datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            dct[col] = value
        return dct

    def save(self):
        db.session.add(self)
        model_updated.send(self, model=self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        model_deleted.send(self, model=self)
        db.session.commit()
        return self
