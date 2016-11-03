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


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()

    torrents = defaultdict(lambda: Torrent())
    print "ts\tihash\tpeers\tup_avg\tdwn_avg\t0_up\t0_dwn\tppm\t0_ppm\trtt_sum\t"
    with open(args.log) as fin:
        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue

            if not message.startswith("peers "):
                continue

            split_msg = message.split("++")

            infohash = split_msg[0].split()[1]

            torrents[infohash].infohash = infohash

            tor = torrents[infohash]
            for i in xrange(0, len(split_msg)):
                msg = split_msg[i].split()

                if not msg or msg[3] == 'None':
                    continue

                idx = 0 if i != 0 else 3

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


            avg_up = 0.0
            avg_dwn = 0.0
            no_up = 0
            no_dwn = 0
            avg_ppm = 0
            no_ppm = 0

            rtt_sum = 0
            peer_count = 0
            for _, p in tor.peers.items():

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
            peer_count = peer_count if peer_count else 1

            avg_up /= peer_count
            avg_dwn /= peer_count
            avg_ppm /= peer_count

            print "%s\t%s\t%d\t%f\t%f\t%d\t%d\t%f\t%d\t%d" % (ts, infohash, peer_count, avg_up,
                                                              avg_dwn, no_up, no_dwn, avg_ppm,
                                                              no_ppm, rtt_sum)

if __name__ == "__main__":
    main()
