#!/usr/bin/env python
from setuptools import setup

# read the contents of your README file
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
      long_description = f.read()


setup(name='hitbtc_wss',
      version='1.0.5',
      description='HitBTC Websocket API Client',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Mike Ellertson',
      author_email='mdellertson@gmail.com',
      packages=['hitbtc_wss'],
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      package_data={'': ['*.md', '*.rst']},
      url='https://github.com/mellertson/hitbtc')

