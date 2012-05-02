#/bin/sh

python2 setup.py sdist
sudo pip-2.7 install -U --no-deps dist/`python2 setup.py --fullname`.tar.gz
