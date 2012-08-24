#!/usr/bin/env python

import sys

import requests

def check_login_required(host, port):
    r = requests.get('http://%(host)s:%(port)s/' % vars(),
                     allow_redirects=False)
    assert r.status_code == 302
    assert False

def main():
    host, port = sys.argv[1], sys.argv[2]
    check_login_required(host, port)


if __name__ == '__main__':
    main()
