import base64
import os
import shutil
import yaml

import boto3
import datetime
from dulwich import client as _mod_client
from dulwich import porcelain
from dulwich.contrib.paramiko_vendor import ParamikoSSHVendor
import png
import requests


def is_png_equal(png1_b64, png2_b64):
    if not png1_b64:
        return False

    images = []

    for b64 in [png1_b64.encode('ascii'), png2_b64.encode('ascii')]:
        reader = png.Reader(bytes=base64.b64decode(b64))
        w, h, pxls, metadata = reader.read_flat()
        images.append((w, h, list(pxls)))

    return images[0] == images[1]


def make_icons_cache(yamlfilename):
    with open(yamlfilename, 'r') as raw:
        contents = yaml.load(raw.read(), Loader=yaml.FullLoader)
    return {item['title']: item['icon'] for item in contents}


_mod_client.get_ssh_vendor = ParamikoSSHVendor
DASH_USERCONTRIB_URL = 'https://london.kapeli.com/feeds/zzz/user_contributed/build/index.json'
ZEAL_API_DOCSETS_URL = 'http://api.zealdocs.org/v1/docsets?filter[where][sourceId]=com.kapeli'


def get_dash_usercontributed_docsets(old_icons):
    docs = sorted(
        requests.get(DASH_USERCONTRIB_URL).json()['docsets'].values(),
        key=lambda d: d['name'].lower()
    )

    res = []
    for doc in docs:
        old_icon = old_icons.get(doc['name'])
        icon = doc.get('icon', doc.get('icon@2x', '""'))
        if old_icon != icon and icon != '""' and is_png_equal(old_icon, icon):
            icon = old_icon
        res.append('- title: %s' % doc['name'])
        res.append('  icon: %s' % icon)

    return '\n'.join(res) + '\n'


def get_dash_docsets(old_icons):
    docs = sorted(
        requests.get(ZEAL_API_DOCSETS_URL).json(),
        key=lambda d: d['title'].lower()
    )

    res = []
    for doc in docs:
        old_icon = old_icons.get(doc['title'])
        icon = doc['icon']
        if old_icon != icon and is_png_equal(old_icon, icon):
            icon = old_icon
        res.append('- title: %s' % doc['title'])
        res.append('  icon: %s' % icon)

    return '\n'.join(res) + '\n'


TARGET = '/tmp/zevdocs.io'
REMOTE = 'ssh://git@github.com/%s'


def data_uri(data):
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def get_daily_downloads(day):
    empty = {'x86_64': [0, 0]}
    return sum([v[0] - v[1] for v in requests.get(
        'https://flathub.org/stats/%s/%02d/%02d.json' % (
            day.year, day.month, day.day
        )
    ).json()["refs"].get("io.github.jkozera.ZevDocs", empty).values()])


def process_repo(remote,
                 with_usercontrib=True,
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
    filename = '%s/_data/docsets.yml' % TARGET
    cache['docsets'] = cache.get('docsets') or get_dash_docsets(make_icons_cache(filename))
    with open(filename, 'w') as f:
        f.write(cache['docsets'])

    if with_usercontrib:
        filename = '%s/_data/docsets_usercontributed.yml' % TARGET
        usercontributed_docsets = get_dash_usercontributed_docsets(make_icons_cache(filename))
        with open(filename, 'w') as f:
            f.write(usercontributed_docsets)
        paths += ['_data/docsets_usercontributed.yml']

    os.chdir(TARGET)
    porcelain.add(paths=paths)
    jk = 'Jeremy Kozera <120114+jkozera@users.noreply.github.com>'
    porcelain.commit(
        message=commit_message or ("Update docset list and weekly downloads %s" % datetime.datetime.now().isoformat()),
        author=jk,
        committer=jk
    )
    commits = [e.commit.tree for e in repo.get_walker(max_entries=2)][:2]
    if sum(1 for _ in repo.object_store.tree_changes(commits[1], commits[0])):
        porcelain.push('.', REMOTE % remote, [b'main:%s' % target_branch.encode('ascii')],
                       key_filename='/tmp/keyfile')
    return cache


def main(json_input=None, context=None):
    process_repo('zealdocs/zealdocs.github.io',
                 with_usercontrib=False,
                 commit_message='chore(data): update docset list',
                 target_branch='main')


if __name__ == '__main__':
    main()
