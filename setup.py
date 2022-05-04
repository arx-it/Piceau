from setuptools import setup

setup(
   name='pickeau',
   version='0.1',
   description='brgm',
   author='brgm',
   author_email='brgm@brgm.fr',
   packages=['pickeau'],  # same as name
   install_requires=['music21'],  # external packages as dependencies
)