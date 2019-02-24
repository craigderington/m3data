#!.env/bin/python
# -*- coding: utf-8 -*-

import unittest
import requests


class APITest(unittest.TestCase):
    def setUp(self):
        self.sms_number = '3212104622'
        self.req_method = 'GET'
        self.url = 'http://localhost:5580/api/v1.0/sms/' + self.sms_number
        self.hdr = {'user-agent': 'SimplePythonFoo()', 'content-type': 'application/json'}

    def runTest(self):
        try:
            r = requests.request(
                self.req_method,
                self.url,
                headers=self.hdr
            )

            self.assertEqual(r.status_code, "200", "Success")

        except requests.HTTPError:
            self.assertEqual(1, 0, "http_error")

    def tearDown(self):
        pass


if __name__ == '__main__':
    APITest.runTest()
