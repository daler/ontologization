import ez_setup
ez_setup.use_setuptools()

import os
import sys
from setuptools import setup

version_py = os.path.join(os.path.dirname(__file__), 'ontologization', 'version.py')
version = open(version_py).read().strip().split('=')[-1].replace('"','')

long_description = """
Wrapper for Ontologizer (http://compbio.charite.de/contao/index.php/ontologizer2.html)
"""

setup(
        name="ontologization",
        version=version,
        install_requires=['requests', 'entabled'],
        packages=['ontologization',
                  'ontologization.data',
                  'ontologization.scripts',
                  ],
        author="Ryan Dale",
        description=long_description,
        long_description=long_description,
        url="none",
        package_data = {'ontologization':["data/*"]},
        package_dir = {"ontologization": "ontologization"},
        scripts = ['ontologization/scripts/download_ontologization_files.py'],
        author_email="dalerr@niddk.nih.gov",
        classifiers=['Development Status :: 4 - Beta'],
    )
