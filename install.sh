#/bin/sh

python setup.py sdist
sudo pip install -U --no-deps dist/`python setup.py --fullname`.tar.gz
