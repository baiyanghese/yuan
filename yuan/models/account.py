# coding: utf-8

import hashlib
import random
from datetime import datetime
from werkzeug import cached_property
from flask.ext.principal import Permission, UserNeed
from ._base import db, YuanQuery, SessionMixin

__all__ = ['Account', 'Member']


class Account(db.Model, SessionMixin):
    query_class = YuanQuery

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, index=True, nullable=False)
    email = db.Column(db.String(200), index=True)

    # user need a password
    password = db.Column(db.String(100))

    screen_name = db.Column(db.String(80))
    description = db.Column(db.String(400))

    # user, org
    account_type = db.Column(db.String(10), default='user')
    org_owner_id = db.Column(db.Integer)

    comment_service = db.Column(db.String(100))

    # for user: 1 - not verified, 2 - verified, > 20 staff > 40 admin
    role = db.Column(db.Integer, default=1)

    created = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        if 'password' in kwargs:
            raw = kwargs.pop('password')
            self.password = self.create_password(raw)
        else:
            self.account_type = 'org'

        if 'name' in kwargs:
            name = kwargs.pop('name')
            self.name = name.lower()

        if 'email' in kwargs:
            email = kwargs.pop('email')
            self.email = email.lower()

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return self.screen_name or self.name

    def __repr__(self):
        return '<Account: %s>' % self.name

    @cached_property
    def avatar(self):
        size = 48
        md5email = hashlib.md5(self.email).hexdigest()
        query = "%s?s=%s%s" % (md5email, size, db.app.config['GRAVATAR_EXTRA'])
        return db.app.config['GRAVATAR_BASE_URL'] + query

    @cached_property
    def comment_service_name(self):
        if self.comment_service:
            return self.comment_service.split('-')[0]
        return None

    @cached_property
    def comment_service_id(self):
        if self.comment_service:
            bits = self.comment_service.split('-')
            return '-'.join(bits[1:])
        return None

    @cached_property
    def permission_write(self):
        if self.account_type == 'user':
            return Permission(UserNeed(self.id))
        q = db.session.query(Member.user_id).filter_by(org_id=self.id)
        needs = map(lambda o: UserNeed(o[0]), q.all())
        return Permission(UserNeed(self.org_owner_id), *needs)

    @cached_property
    def permission_admin(self):
        if self.account_type == 'user':
            return Permission(UserNeed(self.id))
        return Permission(UserNeed(self.org_owner_id))

    @staticmethod
    def create_password(raw):
        salt = Account.create_token(8)
        passwd = '%s%s%s' % (salt, raw,
                             db.app.config['PASSWORD_SECRET'])
        hsh = hashlib.sha1(passwd).hexdigest()
        return "%s$%s" % (salt, hsh)

    @staticmethod
    def create_token(length=16):
        chars = ('0123456789'
                 'abcdefghijklmnopqrstuvwxyz'
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        salt = ''.join([random.choice(chars) for i in range(length)])
        return salt

    def check_password(self, raw):
        if not self.password:
            return False
        if '$' not in self.password:
            return False
        salt, hsh = self.password.split('$')
        passwd = '%s%s%s' % (salt, raw, db.app.config['PASSWORD_SECRET'])
        verify = hashlib.sha1(passwd).hexdigest()
        return verify == hsh

    @property
    def organizations(self):
        if self.account_type == 'org':
            return []
        q = db.session.query(Account).\
                filter_by(account_type='org').\
                join(Member, Member.user_id == self.id)
        data = q.all()
        return data

    @property
    def members(self):
        if self.account_type == 'user':
            return []
        q = db.session.query(Account).\
                filter_by(account_type='user').\
                join(Member, Member.org_id == self.id)
        return q.all()


class Member(db.Model, SessionMixin):
    query_class = YuanQuery

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id', ondelete='CASCADE')
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id', ondelete='CASCADE')
    )

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<Member %s-%s>' % (self.org_id, self.user_id)
