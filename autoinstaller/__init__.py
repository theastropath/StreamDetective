# autoinstaller
# automatically install modules as the user, this helps with APIs and crons that run as a user you don't have permission to install for
import importlib
import importlib.util
import subprocess
import sys

import_names = { 'Mastodon.py': 'mastodon', 'Pillow': 'PIL' }

def check_requirement(r):
    if not r:
        return
    m = import_names.get(r, r)
    need_install = False
    
    try:
        if not importlib.util.find_spec(m):
            # we don't want to install from inside the try block
            need_install = True
    except Exception as e:
        print(r, 'failed to find_spec, need to install,', e, file=sys.stderr)
        need_install = True
    
    if need_install:
        install(r)
        # make sure it installed properly, this especially helps catch missing entries in import_names
        invalidate_caches()
        if not importlib.util.find_spec(m):
            raise Exception('failed to install '+r)


def install(r):
    print('need to install:', r, file=sys.stderr)
    subprocess.run(["pip3", "install", '--user', r], check=True, capture_output=True)


def invalidate_caches():
    importlib.invalidate_caches()
    # workaround for bug in invalidate_caches before python 3.10
    import site
    p = site.getusersitepackages()
    if p not in sys.path:
        sys.path.append(p)

with open('requirements.txt') as requirements:
    for r in requirements:
        check_requirement(r.strip(' \t\n\r'))
