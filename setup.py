#!/usr/bin/env python

try:
    from setuptools.core import setup
except ImportError:
    from distutils.core import setup

setup(name='pyquickcheck',
      version='0.0.0',
      description='a Python port of QuickCheck',
      author='Aaron Griffith',
      author_email='aargri@gmail.com',
      url='http://github.com/agrif/pyquickcheck',
      license='MIT',
      py_modules=['quickcheck'],
)
