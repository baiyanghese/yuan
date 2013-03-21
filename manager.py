# coding: utf-8

import os

from flask.ext.script import Manager
from yuan.app import create_app
from yuan.models import Project

CONFIG = os.path.abspath('./etc/config.py')

app = create_app(CONFIG)
manager = Manager(app)


@manager.command
def runserver(port=5000):
    """Runs a development server."""
    import gevent.monkey
    gevent.monkey.patch_all()

    from gevent.wsgi import WSGIServer
    from werkzeug.serving import run_with_reloader
    from werkzeug.debug import DebuggedApplication

    port = int(port)

    @run_with_reloader
    def run_server():
        print('start server at: 127.0.0.1:%s' % port)
        http_server = WSGIServer(('', port), DebuggedApplication(app))
        http_server.serve_forever()

    run_server()


@manager.command
def createdb():
    """Create a database."""
    from yuan.models import db
    db.create_all()


@manager.command
def initsearch():
    """init search engine."""
    from yuan.elastic import index_project
    for name in Project.all():
        for item in Project.list(name):
            print '%(family)s/%(name)s' % item
            index_project(item, 'update')


@manager.command
def index():
    """index projects."""
    from yuan.models import index_project
    for name in Project.all():
        for item in Project.list(name):
            print '%(family)s/%(name)s' % item
            index_project(item, 'update')


@manager.command
def mirror(url=None):
    """sync a mirror site."""
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all()

    import requests
    from urlparse import urlparse
    from flask import Flask
    if not url:
        url = app.config['MIRROR_URL']

    print '  mirror:', url
    rv = requests.get(url)
    if rv.status_code != 200:
        raise Exception('%s: %s' % url, rv.status_code)

    data = rv.json()

    rv = urlparse(url)
    domain = '%s://%s/repository' % (rv.scheme, rv.netloc)

    def index_with_ctx(config, project):
        app = Flask('mirror')
        app.config = config
        with app.test_request_context():
            _index(project, domain)

    jobs = []
    for project in data:
        me = Project(family=project['family'], name=project['name'])
        if 'updated_at' not in me or \
           _strptime(me['updated_at']) < _strptime(project['updated_at']):
            jobs.append(gevent.spawn(index_with_ctx, app.config, project))

    gevent.joinall(jobs)


def _strptime(t):
    from datetime import datetime
    return datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ')


def _fetch(pkg, domain):
    import urllib
    import requests
    from yuan.models import Package

    url = '%s/%s/%s/%s/' % (
        domain, pkg['family'], pkg['name'], pkg['version'])
    rv = requests.get(url)
    print '   fetch:', url
    if rv.status_code != 200:
        raise Exception('%s: %s' % url, rv.status_code)
    pkg = Package(**rv.json()).save()

    url = '%s%s' % (url, pkg['filename'])
    fpath = os.path.join(
        app.config['WWW_ROOT'], 'repository',
        pkg.family, pkg.name, pkg.version,
        pkg['filename']
    )
    print '    save:', fpath
    urllib.urlretrieve(url, fpath)


def _index(project, domain):
    import requests
    from yuan.models import Package, index_project

    print '    sync: %(family)s/%(name)s' % project
    index_project(project, 'update')

    url = '%s/%s/%s/' % (domain, project['family'], project['name'])
    rv = requests.get(url)
    if rv.status_code != 200:
        raise Exception('%s: %s' % url, rv.status_code)
    data = rv.json()
    if 'versions' not in data:
        data['versions'] = {}

    me = Project(family=project['family'], name=project['name'])

    if 'versions' in me:
        versions = me['versions'].copy()
    else:
        versions = {}

    for v in versions:
        local = versions[v]
        server = None
        if v in data['versions']:
            server = data['versions'][v]

        if not server:
            print '  delete: %s/%s@%s' % (me['family'], me['name'], v)
            pkg = Package(family=me['family'], name=me['name'], version=v)
            pkg.delete()
            # remove this version from project
            Project(**me).remove(v)
        elif 'md5' in server and \
                ('md5' not in local or local['md5'] != server['md5']):
            print '  create: %s/%s@%s' % (me['family'], me['name'], v)
            _fetch(server, domain)
            # add this version to project
            Project(**me).update(server)

    for v in data['versions']:
        if v not in versions:
            pkg = data['versions'][v]
            print '  create: %s/%s@%s' % (pkg['family'], pkg['name'], v)
            _fetch(pkg, domain)
            # add this version to project
            Project(**me).update(pkg)
    return True


if __name__ == '__main__':
    manager.run()
