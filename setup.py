from setuptools import setup, find_packages

setup(
    name     = 'snaked',
    version  = '0.3.dev1',
    author   = 'Anton Bobrov',
    author_email = 'bobrov@vl.ru',
    description = 'Very light and minimalist editor inspired by Scribes',
    long_description = open('README.rst').read(),
    zip_safe   = False,
    packages = find_packages(),
    include_package_data = True,
    namespace_packages = ['snaked', 'snaked.plugins'],
    entry_points = {
        'gui_scripts': [
            'snaked = snaked.core.run:run',
        ]
    },
    url = 'http://github.com/baverman/snaked',    
)
