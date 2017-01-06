#!/usr/bin/env python

import argparse
from collections import defaultdict, namedtuple, OrderedDict

import operator


class PeriodData:
    def __init__(self):
        self.startts = "20161010T101010.100Z"
        self.endts = "20161010T101010.100Z"

        #ihash:maxgain in session
        self.sessiongain = defaultdict(int)

        #ihash:maxgain (netto) in period
        self.maxgain = defaultdict(lambda : -1)

        self.maxdownload = defaultdict(int)
        self.maxupload = defaultdict(int)

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    argparser.add_argument("type", nargs='?', help="type(top|all|normal)", default='normal')
    args = argparser.parse_args()

    total_cm = OrderedDict()

    current_idx = -1
    tlist = []
    # tlist = defaultdict(lambda: PeriodData())

    with open(args.log) as fin:

        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue

            if message.startswith("Selecting"):
                current_idx += 1
                tlist.append(PeriodData())
                tlist[current_idx].startts = ts

                if current_idx > 0:
                    tlist[current_idx-1].endts = ts
            elif message.startswith("Status for"):
                p = message.split(" : ")
                ihash = p[0][-40:]
                q = p[1].split()
                recent_total_download = int(q[0])
                recent_total_upload = int(q[1])

                if tlist[current_idx].sessiongain[ihash] < recent_total_upload - recent_total_download:
                    tlist[current_idx].sessiongain[ihash] = recent_total_upload - recent_total_download

                if tlist[current_idx].maxdownload[ihash] < recent_total_download:
                    tlist[current_idx].maxdownload[ihash] = recent_total_download
                if tlist[current_idx].maxupload[ihash] < recent_total_upload:
                   tlist[current_idx].maxupload[ihash] = recent_total_upload

                clean_dl = recent_total_download - tlist[current_idx-1].maxdownload[ihash]
                clean_ul = recent_total_upload - tlist[current_idx-1].maxupload[ihash]

                tlist[current_idx].maxgain[ihash] = clean_ul - clean_dl

    if args.type is 'normal':
        print "idx\tstartts\tendts\tihash\tsgain\tpgain\tmaxdl\tmaxul"
        for idx, item in enumerate(tlist):
            for ihash, _ in item.sessiongain.items():
                print "%d\t%s\t%s\t%s\t%s\t%s\t%d\t%d\t" \
                      %(idx, item.startts, item.endts, ihash, item.sessiongain[ihash], item.maxgain[ihash],
                        item.maxdownload[ihash], item.maxupload[ihash])
    elif args.type == 'top':
        top_val = 3
        print "idx\tstartts\tendts\tihash"
        for idx, item in enumerate(tlist):
            sortedgain = sorted(item.maxgain.items(), key=operator.itemgetter(1), reverse=True)
            for ihash, gain in sortedgain[:top_val]:
                print "%d\t%s\t%s\t%s\t%s" %(idx, item.startts, item.endts, ihash, gain)
    elif args.type == 'all':
        top_val = 6
        print "idx\tstartts\tendts\tihash"
        for idx, item in enumerate(tlist):
            sortedgain = sorted(item.sessiongain.items(), key=operator.itemgetter(1), reverse=True)
            for ihash, gain in sortedgain[:top_val]:
                print "%d\t%s\t%s\t%s\t%s" %(idx, item.startts, item.endts, ihash, gain)

if __name__ == "__main__":
    main()
