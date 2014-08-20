#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a test DAL server for testing pyvo.dal
"""
from __future__ import print_function, division

# this gets around a bug in astropy 0.2.4 (needed for python3 support)
from ... import dal

import os
import sys
import shutil
import re
import threading
import socket
import urllib2
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from astropy.utils.data import get_pkg_data_filename

try:
    from astropy.tests.disable_internet import (turn_on_internet, 
                                                turn_off_internet, INTERNET_OFF)
except:
    # for astropy ver < 0.4
    def turn_on_internet(verbose=False): pass
    def turn_off_internet(verbose=False): pass
    INTERNET_OFF = False

siaresult = "data/neat-sia.xml"
scsresult = "data/twomass-cs.xml"
errresult = "data/error-sia.xml"
ssaresult = "data/jhu-ssa.xml"
slaresult = "data/nrao-sla.xml"

class TestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = re.split(r'\?', self.path, 1)[0]

        try:
            if path.startswith("/path"):
                self.send_path()
            elif path.startswith("/dal/"):
                self.send_file(path[len("/dal/"):])
            elif path.startswith("/err"):
                self.send_err()
            elif path == "/sia":
                self.send_sia()
            elif path == "/cs":
                self.send_scs()
            elif path == "/ssa":
                self.send_ssa()
            elif path == "/sla":
                self.send_sla()
            elif path == "/shutdown":
                self.send_empty()
                # self.shutdown()
            else:
                try:
                    self.send_error(404)
                    self.end_headers()
                except socket.error as ex:
                    if ex.errno != 104:
                        print("Test Server: Detected socket error while serving "+
                              path+": " + str(ex))
        except Exception as ex:
            print("Test Server failure (port="+str(self._port)+"): "+str(ex))
            raise RuntimeError("test server error ("+type(ex)+"): "+str(ex))
                

    def send_path(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-Length", len(self.path)+1)
        self.end_headers()
        self.wfile.write(self.path+"\n")

    def send_err(self):
        self.send_file(errresult)

    def send_sia(self):
        self.send_file(siaresult)

    def send_scs(self):
        self.send_file(scsresult)

    def send_ssa(self):
        self.send_file(ssaresult)

    def send_sla(self):
        self.send_file(slaresult)

    def send_file(self, filename):
        path = get_pkg_data_filename(filename)
        f = open(path,'rb')

        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-Length", os.fstat(f.fileno())[6])
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def send_empty(self):
        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-Length", 0)
        self.end_headers()

    def log_message(format, *args):
        pass

_ports_in_use = []

class TestServer(threading.Thread):

    def __init__(self, port=None, timeout=5):
        threading.Thread.__init__(self)
        if not port:
            port = find_available_port()
        self._reserve_port(port)
        self._port = port
        self._timeout = timeout
        self.httpd = None
        self.internet_init_off = INTERNET_OFF

    def _reserve_port(self, port):
        _ports_in_use.append(port)

    def _release_port(self, port):
        if port in _ports_in_use:
            _ports_in_use.remove(port)

    def _del_(self):
        self._release_port(self._port)

    @property
    def port(self):
        return self._port

    def run(self):
        turn_on_internet(True)
        self.httpd = HTTPServer(('', self._port), TestHandler)
        self.httpd.timeout = self._timeout
        self.httpd.serve_forever()

    def shutdown(self, timeout=None):
        if not timeout:
            timeout = self._timeout+1
        if self.httpd:  
            self.httpd.shutdown()
            self.join(timeout)
            self.httpd = None
        if self.internet_init_off:
            turn_off_internet(True)

def run():
    httpd = HTTPServer(('', 8081), TestHandler)
    httpd.timeout = 12
    httpd.handle_request()
    # httpd.serve_forever()
    # os.sleep(12)
    # httpd.shutdown()

def server_running(port=8081):
    url = "http://localhost:{0}/path".format(port)
    try:
        strm = urllib2.urlopen(url);
        if strm.getcode() < 1: 
            return False
        return True
    except IOError:
        return False

def find_available_port(baseport=8081, limit=8181, step=1):
    port = baseport
    while port < limit:
        if port not in _ports_in_use and not server_running(port):
            return port
        port += step

def get_server(baseport=8081, limit=8181, step=1):
    return TestServer(find_available_port(baseport, limit, step))

        

if __name__ == "__main__":
    run()

