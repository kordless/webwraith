import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        subprocess.check_call(['playwright', 'install', 'chromium'])

setup(
    name='webwraith',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'playwright',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        webwraith=webwraith.cli:cli
    ''',
    cmdclass={
        'install': PostInstallCommand,
    },
)