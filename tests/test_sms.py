#!.env/bin/python
# -*- coding: utf-8 -*-

import time
import requests
import csv
from config import basedir


def make_call(sms_number):
    """
    Call the API
    :param sms_number:
    :return:
    """

    api_method = 'GET'
    url = 'http://localhost:5880/api/v1.0/sms/' + sms_number
    hdr = {'user-agent': 'SimplePythonFoo()', 'content-type': 'application/json'}

    try:
        r = requests.request(
            api_method,
            url,
            headers=hdr
        )

        if r.status_code == 200:
            resp = r.json()
            print(resp)

        else:
            resp = r.status_code
            print('The API call returned Response: {}'.format(str(resp)))

    except requests.HTTPError as http_err:
        print('HTTP Error: {}'.format(str(http_err)))


def read_file(filepath):
    """
    Read the CSV File
    :param filepath:
    :return: counter
    """
    counter = 0
    try:
        with open(filepath, 'r') as f1:
            reader = csv.reader(f1, delimiter=',')
            for row in reader:
                sms = str(row[1])
                make_call(sms)
                counter += 1
    except IOError as io_err:
        print('Data file access error: {}'.format(str(io_err)))

    return counter


def main():
    """
    Enter the Program
    :return:
    """

    filepath = basedir + '/assets/data/home_phone__email.csv'

    try:
        print('Successfully tested {} records'.format(str(read_file(filepath))))

    except IOError as e:
        print(e)


if __name__ == '__main__':
    t1 = time.time()
    print('Starting testing engine...')
    main()
    print('Finished!')
    t2 = time.time()
    print('Script completed in {0:.2f} seconds'.format(t2 - t1))
