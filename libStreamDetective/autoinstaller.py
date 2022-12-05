import importlib
import subprocess

def check_requirement(r):
    try:
        i = importlib.import_module(r)
    except Exception as e:
        print(r, 'failed to load, need to install')
        subprocess.run(["pip3", "install", r])


with open('requirements.txt') as requirements:
    for r in requirements:
        check_requirement(r.strip(' \t\n\r'))
