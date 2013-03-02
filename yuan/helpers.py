import functools
import time
import hashlib
import base64
from flask import g, request, session, current_app
from flask import flash, url_for, redirect, abort
from flask.ext.babel import lazy_gettext as _
from .models import Account


class require_role(object):
    def __init__(self, role):
        self.role = role

    def __call__(self, method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            if not g.user:
                url = url_for('account.signin')
                if '?' not in url:
                    url += '?next=' + request.url
                return redirect(url)
            if self.role is None:
                return method(*args, **kwargs)
            if g.user.id == 1:
                # this is superuser, have no limitation
                return method(*args, **kwargs)
            if g.user.role == 1:
                flash(_('Please verify your email'), 'warn')
                return redirect('/account/settings')
            if g.user.role < self.role:
                return abort(403)
            return method(*args, **kwargs)
        return wrapper


require_login = require_role(None)
require_user = require_role(2)


def get_current_user():
    if 'id' in session and 'token' in session:
        user = Account.query.get(int(session['id']))
        if not user:
            return None
        if user.password != session['token']:
            return None
        return user

    auth = request.headers.get('Authorization', None)
    if auth and auth.startswith('Yuan '):
        code = auth.replace('Yuan ', '', 1)
        return verify_auth_token(code)
    return None


def login_user(user, permanent=False):
    if not user:
        return None
    session['id'] = user.id
    session['token'] = user.password
    if permanent:
        session.permanent = True
    return user


def logout_user():
    if 'id' not in session:
        return
    session.pop('id')
    session.pop('token')


def create_auth_token(user):
    timestamp = int(time.time())
    secret = current_app.secret_key
    token = '%s%s%s%s' % (secret, timestamp, user.id, user.password)
    hsh = hashlib.sha1(token).hexdigest()
    return base64.b32encode('%s|%s|%s' % (timestamp, user.id, hsh))


def verify_auth_token(token, expires=30):
    try:
        token = base64.b32decode(token)
    except:
        return None
    bits = token.split('|')
    if len(bits) != 3:
        return None
    timestamp, user_id, hsh = bits
    try:
        timestamp = int(timestamp)
        user_id = int(user_id)
    except:
        return None
    delta = time.time() - timestamp
    if delta < 0:
        return None
    if delta > expires * 60 * 60 * 24:
        return None
    user = Account.query.get(user_id)
    if not user:
        return None
    secret = current_app.secret_key
    _hsh = hashlib.sha1(
        '%s%s%s%s' % (secret, timestamp, user_id, user.password)
    )
    if hsh == _hsh.hexdigest():
        return user
    return None
