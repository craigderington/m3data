#! /usr/bin/python3.6
import os
import sys
import logging

activate_this = '/home/craigderington/sites/m3data/.env/bin/activate_this.py'

with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))


logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/craigderington/sites/m3data/')

from app import app as application
application.secret_key = os.urandom(64)
