#!/usr/bin/env python

import sys
from os import path as path
from sys import path as pythonpath, stdout

from twisted.internet import reactor

pythonpath.append(path.abspath(path.join(path.dirname(__file__), "python-bittorrent")))

import tracker
from bittorrent import Tracker

def _decode_request(path):
    if path[:1] == "?":
        path = path[1:]
    elif path[:2] == "/?":
        path = path[2:]
    elif path[:10] == "/announce?":
        path = path[10:]

    return tracker.parse_qs(path)

tracker.decode_request = _decode_request

print >> stdout, "Run tracker"

track = Tracker(port=9197, log=None)
track.run()

reactor.exitCode = 0
reactor.run()

print >> stdout, "Stopping tracker"
track.stop()

sys.exit(reactor.exitCode)
