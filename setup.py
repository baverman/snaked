from setuptools import setup, find_packages
from setuptools.command import easy_install

from snaked import VERSION

def install_script(self, dist, script_name, script_text, dev_path=None):
    script_text = easy_install.get_script_header(script_text) + (
        ''.join(script_text.splitlines(True)[1:]))

    self.write_script(script_name, script_text, 'b')

easy_install.easy_install.install_script = install_script

setup(
    name     = 'snaked',
    version  = VERSION,
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'Very light and minimalist editor inspired by Scribes',
    long_description = open('README.rst').read(),
    zip_safe   = False,
    packages = find_packages(exclude=('tests', 'tests.*')),
    data_files = [('snaked/completion/bash',['completion/bash/snaked'])],
    install_requires = ['chardet', 'uxie', 'supplement'],
    include_package_data = True,
    scripts = ['bin/snaked'],
    url = 'http://github.com/baverman/snaked',
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Natural Language :: English",
        "Topic :: Text Editors"
    ],
)
