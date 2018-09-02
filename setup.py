from setuptools import setup

setup(name='hitbtc',
      version='1.0.5',
      description='HitBTC Websocket API Client',
      author='Mike Ellertson',
      author_email='mdellertson@gmail.com',
      packages=['hitbtc'],
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      install_requires=['websocket-client'],
      package_data={'': ['*.md', '*.rst']},
      url='https://github.com/mellertson/hitbtc')

