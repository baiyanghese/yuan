# coding: utf-8

from flask import g
from flask.ext.admin import Admin, AdminIndexView, expose
from flask.ext.admin.contrib.sqlamodel import ModelView
from ..models import db, Account


class BaseView(ModelView):
    column_display_pk = True
    can_create = False
    can_edit = False

    def is_accessible(self):
        if not g.user:
            return False
        if g.user.id == 1:
            return True
        if g.user.account_type != 'user':
            return False
        return g.user.role > 40


class HomeView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')

    def is_accessible(self):
        if not g.user:
            return False
        if g.user.id == 1:
            return True
        if g.user.account_type != 'user':
            return False
        return g.user.role > 40


class UserView(BaseView):
    can_edit = True
    column_exclude_list = ('password', 'token', 'description')
    form_excluded_columns = ('password', 'created', 'token')


admin = Admin(name='Yuan', index_view=HomeView())
admin.add_view(UserView(Account, db.session))
