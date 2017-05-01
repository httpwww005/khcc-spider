from __future__ import print_function
import json
import sys
from bottle import get, post, route, run, template, request
from datetime import datetime
from datetime import date
from bottle import response
import subprocess

import logging
logger = logging.getLogger()

import os
import pymongo
import gridfs
import pytz
from bson.codec_options import CodecOptions

TZ=pytz.timezone("Asia/Taipei")

MONGODBCSV_URI=os.environ["MONGODBCSV_URI"]
client_csv = pymongo.MongoClient(MONGODBCSV_URI)
db_csv = client_csv["csv"]
fs_db = gridfs.GridFS(db_csv)

magic_word = os.environ.get("MAGIC_WORD", None)


def save_csv(new_date):
    home = os.environ.get("HOME", None)
    csv_file = os.path.join(home, "visitcount.csv") 

    new_filename = "%s.csv" % new_date

    with open(csv_file, 'r') as fp_local:
        with fs_db.new_file(filename=new_filename) as fp_remote:
            fp_remote.write(fp_local.read())


def run_spider():
    cmd = os.environ.get("SCRAPY_CMD", None)
    logging.debug('Late night crawler is running: %s' % cmd)
    process = subprocess.Popen(cmd, shell=True)
    process.wait()

    new_date = str(datetime.now(TZ).date())
    logging.debug('save visitcount.csv as %s.csv in gridfs' % new_date)
    save_csv(new_date)


@post('/')
def index():
    body = request.body.read()
    if body == magic_word:
        run_spider()
        print("OK", file=sys.stderr)
        return "OK"
    else:
        return ""


port = int(os.environ.get('PORT',5000))
run(host='0.0.0.0', port=port, debug=False, reloader=True)
