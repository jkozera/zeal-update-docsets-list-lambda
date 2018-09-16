import base64
import os
import shutil

import boto3
import datetime
from dulwich import client as _mod_client
from dulwich import porcelain
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor
import requests

from . import sparklines



_mod_client.get_ssh_vendor = ParamikoSSHVendor
DASH_USERCONTRIB_URL = 'https://london.kapeli.com/feeds/zzz/user_contributed/build/index.json'
ZEAL_API_DOCSETS_URL = 'http://api.zealdocs.org/v1/docsets?filter[where][sourceId]=com.kapeli'


def get_dash_usercontributed_docsets():
    docs = sorted(
        requests.get(DASH_USERCONTRIB_URL).json()['docsets'].values(),
        key=lambda d: d['name'].lower()
    )

    res = []
    for doc in docs:
        res.append('- title: %s' % doc['name'])
        res.append('  icon: %s' % doc.get('icon', doc.get('icon@2x', '""')))

    return '\n'.join(res) + '\n'


def get_dash_docsets():
    docs = sorted(
        requests.get(ZEAL_API_DOCSETS_URL).json(),
        key=lambda d: d['title'].lower()
    )

    res = []
    for doc in docs:
        res.append('- title: %s' % doc['title'])
        res.append('  icon: %s' % doc['icon'])

    return '\n'.join(res) + '\n'


TARGET = '/tmp/zevdocs.io'
REMOTE = 'ssh://git@github.com/%s'


def data_uri(data):
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def get_daily_downloads(day):
    return sum([v[0] - v[1] for v in requests.get(
        'https://flathub.org/stats/%s/%02d/%02d.json' % (
            day.year, day.month, day.day
        )
    ).json()["refs"]["io.github.jkozera.ZevDocs"].values()])


def process_repo(remote,
                 with_usercontrib=True,
                 with_downloads=True,
                 commit_message=None,
                 target_branch='gh-pages',
                 cache=None):
    cache = cache or {}

    try:
        shutil.rmtree(TARGET)
    except FileNotFoundError:
        pass

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('deploy-keys')
    key = table.get_item(Key={'repo_name': remote})['Item']['key']
    with open('/tmp/keyfile', 'w') as keyfile:
        keyfile.write(key)

    repo = porcelain.clone(
        REMOTE % remote, TARGET,
        key_filename='/tmp/keyfile'
    )

    try:
        os.makedirs('%s/_data' % TARGET)
    except FileExistsError:
        pass

    paths = ['_data/docsets.yml']
    cache['docsets'] = cache.get('docsets') or get_dash_docsets()
    with open('%s/_data/docsets.yml' % TARGET, 'w') as f:
        f.write(cache['docsets'])

    if with_usercontrib:
        usercontributed_docsets = get_dash_usercontributed_docsets()
        with open('%s/_data/docsets_usercontributed.yml' % TARGET, 'w') as f:
            f.write(usercontributed_docsets)
        paths += ['_data/docsets_usercontributed.yml']

    if with_downloads:
        with open('%s/_data/weekly_downloads.yml' % TARGET, 'w') as f:
            today = datetime.date.today()
            weekly_downloads = [
                get_daily_downloads(today - datetime.timedelta(days=days))
                for days in range(7, 0, -1)
            ]
            sparkline = data_uri(sparklines.impulse(
                weekly_downloads,
                below_color='yellow',
                above_color='MediumSpringGreen',
                width=3,
                dmin=0,
                dmax=max(weekly_downloads)
            ))
            f.write('count: %s\n' % sum(weekly_downloads))
            f.write('sparkline: %s\n' % sparkline)
        paths += ['_data/weekly_downloads.yml']

    os.chdir(TARGET)
    porcelain.add(paths=paths)
    jk = 'Jerzy Kozera <jerzy.kozera@gmail.com>'
    porcelain.commit(
        message=commit_message or ("Update docset list and weekly downloads %s" % datetime.datetime.now().isoformat()),
        author=jk,
        committer=jk
    )
    commits = [e.commit.tree for e in repo.get_walker(max_entries=2)][:2]
    if sum(1 for _ in repo.object_store.tree_changes(commits[1], commits[0])):
        porcelain.push('.', REMOTE % remote, [b'master:%s' % target_branch.encode('ascii')],
                       key_filename='/tmp/keyfile')

def main(json_input=None, context=None):
    cache = process_repo('jkozera/zevdocs.io')
    process_repo('zealdocs/zealdocs.github.io',
                 with_usercontrib=False,
                 with_downloads=False,
                 commit_message='chore(data): update docset list',
                 target_branch='master',
                 cache=cache)

if __name__ == '__main__':
    main()
