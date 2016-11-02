#!/usr/bin/env python

import argparse
from collections import defaultdict


class Peer:
    def __init__(self):
        self.infohash = "0" * 40
        self.ip = "0.0.0.0"
        self.uprate_peak = 0
        self.dwnrate_peak = 0
        self.rtt = 0
        self.progress = 0.0
        self.num_pieces = 0.0
        self.pieces = []
        self.connection_type = -1

        self.flags = {}


class Torrent:
    def __init__(self):
        self.infohash = "0" * 40
        self.peers = defaultdict(lambda: Peer())


def printing(ttr, type):
    for infohash, tor in ttr.iteritems():
        avg_up = 0.0
        avg_dwn = 0.0
        no_up = 0
        no_dwn = 0
        avg_ppm = 0
        no_ppm = 0

        rtt_sum = 0
        peer_count = 0
        for _, p in tor.peers.items():

            # do not include BEP 17 and 19
            if p.connection_type is not "0":
                continue

            peer_count += 1

            no_up += 1 if p.uprate_peak == 0 else 0
            no_dwn += 1 if p.dwnrate_peak == 0 else 0
            no_ppm += 1 if p.progress == 0 else 0

            avg_up += float(p.uprate_peak)
            avg_dwn += float(p.dwnrate_peak)
            avg_ppm += float(p.progress)

            rtt_sum += int(p.rtt)

        # prevent divided by zero
        peer_count_c = peer_count if peer_count else 1

        avg_up /= peer_count_c
        avg_dwn /= peer_count_c
        avg_ppm /= peer_count_c

        print "%s\t%d\t%f\t%f\t%d\t%d\t%f\t%d\t%d\t%d" % (infohash, peer_count, avg_up,
                                                          avg_dwn, no_up, no_dwn, avg_ppm,
                                                          no_ppm, rtt_sum, type)

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()

    torrents = defaultdict(lambda: Torrent())
    torrents2 = defaultdict(lambda: Torrent())
    print "ihash\tpeers\tup_avg\tdwn_avg\t0_up\t0_dwn\tppm\t0_ppm\trtt_sum\ttype"
    with open(args.log) as fin:
        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, _, message = line.split("-", 2)
            except ValueError:
                continue

            if not (message.startswith("peers ") or message.startswith("finishpeers ")):
                continue

            split_msg = message.split("++")

            infohash = split_msg[0].split()[1]

            torrents[infohash].infohash = infohash
            torrents2[infohash].infohash = infohash

            tor1 = torrents[infohash]
            tor2 = torrents2[infohash]
            for i in xrange(0, len(split_msg)):
                msg = split_msg[i].split()

                if not msg or msg[3] == 'None':
                    continue

                idx = 0 if i != 0 else 3

                tor = tor1 if message.startswith("peers ") else tor2

                ip = msg[1+idx].split(":")[1]
                tor.peers[ip].ip = ip
                tor.peers[ip].infohash = infohash
                peaks = msg[6+idx].split(":")[1].split("/")
                tor.peers[ip].uprate_peak = float(peaks[0])
                tor.peers[ip].dwnrate_peak = float(peaks[1])
                tor.peers[ip].progress = float(msg[5+idx].split(":")[1])

                tor.peers[ip].num_pieces = msg[4+idx].split(":")[1]
                tor.peers[ip].rtt = msg[11+idx].split(":")[1]
                # tor.peers[ip].pieces = msg[13+idx]
                tor.peers[ip].connection_type = msg[12+idx].split(":")[1]

                # torrent:619fff16595b2e708a9b66a6fe9a21c0d27049f1 ip:78.175.188.236-14350   uprate:0   dwnrate:0
                # #piece:0        progress:0      peak-up/down:0/0        speed:0 remote:False/True
                # # we:False/True   source:3        rtt:0   contype:0       recipro:16000

        # peer that detected just after finish
        printing(torrents2, 1)

        # peer that detected after wait for some time
        printing(torrents, 2)


if __name__ == "__main__":
    main()
