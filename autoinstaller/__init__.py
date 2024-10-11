# autoinstaller
# automatically install modules as the user, this helps with APIs and crons that run as a user you don't have permission to install for
import importlib
import subprocess
import sys
import os.path
import pkg_resources

def check_requirement(r):
    if not r:
        return
    need_install = False
    
    try:
        pkg_resources.require(r)
    except Exception as e:
        print(r, 'failed to pkg_resources.require, need to install,', e, file=sys.stderr)
        need_install = True
    
    if need_install:
        install(r)
        # make sure it installed properly, this especially helps catch missing entries in import_names
        #pkg_resources.require(r)

def install(r):
    print('need to install:', r, file=sys.stderr)
    subprocess.run(['pipx', 'upgrade', r], check=True)#, capture_output=True)
    invalidate_caches()


def invalidate_caches():
    importlib.invalidate_caches()
    # workaround for bug in invalidate_caches before python 3.10
    import site
    p = site.getusersitepackages()
    if p not in sys.path:
        sys.path.append(p)

file = os.path.dirname(__file__)
file = os.path.realpath(file)
file = os.path.dirname(file)
file = os.path.join(file, 'requirements.txt')

with open(file) as requirements:
    for r in requirements:
        check_requirement(r.strip(' \t\n\r'))
