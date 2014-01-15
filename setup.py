#!/usr/bin/env python

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

setup(name='pyquickcheck',
      version='0.0.0',
      description='a Python port of QuickCheck',
      author='Aaron Griffith',
      author_email='aargri@gmail.com',
      url='http://github.com/agrif/pyquickcheck',
      license='MIT',
      packages=find_packages(),
      setup_requires = ['setuptools_git >= 0.3'],
)
