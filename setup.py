import sys
from setuptools import setup, find_packages
from os import path, makedirs
from shutil import copy
import platform

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


py_ver = sys.version_info
with open("requirements.txt", "r") as f:
    requirements = list(f.readlines())
if py_ver[1] < 5:
    requirements.append('typing')
if py_ver[1] < 4:
    requirements.append('enum')

setup(
    name='keever',
    version='0.0.1',
    python_requires='>=3.3, <4',
    description='Model, database and algorithm manager.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kaeryv/keever',
    author='Kaeryv',
    author_email='nicolas.roy@unamur.be',
    classifiers=[  
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Games/Entertainment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    keywords='surrogate modeling photonics model',

    packages=['keever'],
    install_requires=requirements,
 
    project_urls={  # Optional
        'Bug Reports': 'https://github.com/kaeryv/keever/issues',
        'Source': 'https://github.com/kaeryv/keever/',
    },
)
