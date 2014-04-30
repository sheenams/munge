"""
Create unix package:    python setup.py sdist
"""

import os
import subprocess
import shutil
from distutils.core import setup
from os.path import join

subprocess.call('git log --pretty=format:%h -n 1 > munging/data/sha', shell = True)
subprocess.call('git shortlog --format="XXYYXX%h" | grep -c XXYYXX > munging/data/ver', shell = True)

from munging import __version__
from munging.scripts import script

params = {'author': 'Noah Hoffman',
          'author_email': 'ngh2@uw.edu',
          'description': script.__doc__.strip(),
          'name': 'munging',
          'packages': ['munging','munging.scripts','munging.subcommands'],
          'package_dir': {'munging': 'munging'},
          'scripts': ['munge'],
          'version': __version__,
          'package_data': {'munging': [join('data',f) for f in ['sha','ver']]}
          }
    
setup(**params)

