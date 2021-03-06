#!/usr/bin/env python

# since this may be run under py2
from __future__ import print_function

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
from subprocess import Popen, PIPE
import sys
import os

def find_version():
    try:
        p = Popen('git describe --tags --match "v*.*"', stdout=PIPE, stderr=PIPE, shell=True)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        line = line.decode().strip()
        if line.startswith('v'):
            line = line[1:]
            return line
    except Exception as e:
        pass
    
    # if we get here, git tags failed
    # attempt to read PKG-INFO
    try:
        with open("PKG-INFO") as f:
            for line in f.readlines():
                line = line.strip().split(": ")
                if line[0] == "Version":
                    return line[1]
    except Exception:
        pass
    
    # if we get HERE, nothing worked
    print("warning: git version or PKG-INFO file not found. version will be wrong!", file=sys.stderr)
    return "0.0-unknown"

if __name__ == '__main__':
    # put check here, because sphinx might be py2
    if sys.hexversion < 0x03020000:
        raise RuntimeError('This package requires Python 3.2 or later.')
    
    # force this to run in the right directory
    os.chdir(os.path.abspath(os.path.split(__file__)[0]))
    
    setup(name='pyquickcheck',
          version=find_version(),
          description='a Python port of QuickCheck',
          author='Aaron Griffith',
          author_email='aargri@gmail.com',
          url='http://github.com/agrif/pyquickcheck',
          license='MIT',
          packages=find_packages(),
          test_suite='quickcheck.tests',
          setup_requires = ['setuptools_git >= 0.3'],
    )
