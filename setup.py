from setuptools import setup
from os import path

with open(path.join(path.abspath(path.dirname(__file__)), 'README.md'), 'r') as f:
    long_description = f.read()

setup(
    name='python-softdev',
    version='0.2.12',
    packages=['softdev'],
    scripts=['bin/softdev-startproject'],
    url='',
    license='MIT License',
    author='Michel Fodje',
    author_email='michel.fodje@lightsource.ca',
    description='Python Soft Device Support for EPICS',
    long_description=long_description,
    long_description_content_type='text/markdown'
)
