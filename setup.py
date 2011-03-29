from setuptools import setup, find_packages

setup(
    name     = 'snaked',
    version  = '0.4.7',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'Very light and minimalist editor inspired by Scribes',
    long_description = open('README.rst').read(),
    zip_safe   = False,
    packages = find_packages(exclude=('tests', )),
    install_requires = ['chardet'],
    include_package_data = True,
    namespace_packages = ['snaked', 'snaked.plugins'],
    entry_points = {
        'gui_scripts': [
            'snaked = snaked.core.run:run',
        ]
    },
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
