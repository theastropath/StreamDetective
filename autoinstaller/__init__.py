import importlib
import importlib.util
import subprocess
import sys

import_names = { 'Mastodon.py': 'mastodon' }

def check_requirement(r):
    m = import_names.get(r, r)
    need_install = False
    
    try:
        if not importlib.util.find_spec(m):
            need_install = True
    except Exception as e:
        print(r, 'failed to find_spec, need to install,', e)
        need_install = True
    
    if need_install:
        install(r)
        # make sure it installed properly, this especially helps catch missing entries in import_names
        importlib.invalidate_caches()
        import site
        p = site.getusersitepackages()
        if not p in sys.path:
            sys.path.append(p)
        #importlib.import_module(m)
        if not importlib.util.find_spec(m):
            raise Exception('failed to install '+r)


def install(r):
    print('need to install:', r)
    subprocess.run(["pip3", "install", '--user', r], check=True, capture_output=True)
    #pip.main(['install', '--user', r])


with open('requirements.txt') as requirements:
    for r in requirements:
        check_requirement(r.strip(' \t\n\r'))
