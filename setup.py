import setuptools
from setuptools import setup

setup(
    name='Tornado-Tester',
    version='0.1.1',
    packages=setuptools.find_packages('tornado_tester'),
    url='https://github.com/hardtack/tornado-tester',
    license='MIT LICENSE',
    author='Geonu Choi',
    author_email='6566gun@gmail.com',
    install_requires=['tornado'],
    description='Testing tornado web application in any testing libraries.'
)
