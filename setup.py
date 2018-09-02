from setuptools import setup

VERSION = '1.0.5'

setup(name='hitbtc-wss',
      version=VERSION,
      description='HitBTC Websocket API Client',
      author='Mike Ellertson',
      author_email='mdellertson@gmail.com',
      packages=['hitbtc-wss'],
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      install_requires=['websocket-client'],
      package_data={'': ['*.md', '*.rst']})

