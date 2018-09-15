import base64
import datetime
import json
import os
import shutil

import boto3
from dulwich import client as _mod_client
from dulwich import porcelain
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor
import requests


_mod_client.get_ssh_vendor = ParamikoSSHVendor
DASH_USERCONTRIB_URL = 'https://london.kapeli.com/feeds/zzz/user_contributed/build/index.json'
ZEAL_API_DOCSETS_URL = 'http://api.zealdocs.org/v1/docsets?filter[where][sourceId]=com.kapeli'


def get_dash_usercontributed_docsets():
    docs = sorted(
        requests.get(DASH_USERCONTRIB_URL).json()['docsets'].values(),
        key=lambda d: d['name'].lower()
    )

    res = ['docsets:']
    for doc in docs:
        res.append('- title: %s' % doc['name'])
        res.append('  icon: %s' % doc.get('icon', doc.get('icon@2x', '""')))

    return '\n'.join(res)


def get_dash_docsets():
    docs = sorted(
        requests.get(ZEAL_API_DOCSETS_URL).json(),
        key=lambda d: d['title'].lower()
    )

    res = ['docsets:']
    for doc in docs:
        res.append('- title: %s' % doc['title'])
        res.append('  icon: %s' % doc['icon'])

    return '\n'.join(res)


TARGET = '/tmp/zevdocs.io'
REMOTE = 'ssh://git@github.com/jkozera/zevdocs.io'


def main(json_input=None, context=None):
    try:
        shutil.rmtree(TARGET)
    except FileNotFoundError:
        pass

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('deploy-keys')
    key = table.get_item(Key={'repo_name': 'jkozera/zevdocs.io'})['Item']['key']
    with open('/tmp/keyfile', 'w') as keyfile:
        keyfile.write(key)
    repo = porcelain.clone(
        REMOTE, TARGET,
        key_filename='/tmp/keyfile'
    )

    try:
        os.makedirs('%s/_data' % TARGET)
    except FileExistsError:
        pass

    docsets = get_dash_docsets()
    with open('%s/_data/docsets.yml' % TARGET, 'w') as f:
        f.write(docsets)

    usercontributed_docsets = get_dash_usercontributed_docsets()
    with open('%s/_data/docsets_usercontributed.yml' % TARGET, 'w') as f:
        f.write(usercontributed_docsets)

    os.chdir(TARGET)
    porcelain.add(paths=['_data/docsets.yml', '_data/docsets_usercontributed.yml'])
    jk = 'Jerzy Kozera <jerzy.kozera@gmail.com>'
    porcelain.commit(
        message="Update docset list %s" % datetime.datetime.now().isoformat(),
        author=jk,
        committer=jk
    )
    commits = [e.commit.tree for e in repo.get_walker(max_entries=2)][:2]
    if sum(1 for _ in repo.object_store.tree_changes(commits[1], commits[0])):
        porcelain.push('.', REMOTE, [b'master:gh-pages'],
                       key_filename='/tmp/keyfile')


if __name__ == '__main__':
    main()
