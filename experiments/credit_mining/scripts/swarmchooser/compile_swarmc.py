#!/usr/bin/env python

import argparse
from collections import defaultdict, namedtuple, OrderedDict

import operator
from os import path


class PeriodData:
    def __init__(self):
        self.startts = "20161010T101010.100Z"
        self.endts = "20161010T101010.100Z"

        self.sessiongain = -1
        self.maxgain = -1
        self.ihash = "0" * 40
        self.istopthree = False

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("alltop", help="all top used as input")
    argparser.add_argument("allses", help="all session used as input")

    args = argparser.parse_args()

    current_idx = -1
    count = 0
    tlist = []

    with open(args.alltop) as fat, open(args.allses) as fas:
        for line in fat:
            if line.startswith('idx'):
                continue
            spline = line.split()
            if int(spline[0]) == current_idx + 1:
                if len(tlist) < int(spline[0]) + 1:
                    tlist.append(defaultdict(lambda: PeriodData()))
                count = 0
            current_idx = int(spline[0])

            count += 1

            ihash = spline[3]
            topgain = int(spline[4])

            tlist[current_idx][ihash].maxgain = topgain
            tlist[current_idx][ihash].ihash = ihash
            tlist[current_idx][ihash].istopthree = count <= 3

        current_idx = -1
        for line in fas:
            if line.startswith('idx'):
                continue
            spline = line.split()
            if int(spline[0]) == current_idx + 1:
                if len(tlist) < int(spline[0]) + 1:
                    tlist.append(defaultdict(lambda: PeriodData()))
                count = 0
            current_idx = int(spline[0])

            count += 1

            ihash = spline[3]
            topgain = int(spline[4])

            tlist[current_idx][ihash].sessiongain = topgain
            tlist[current_idx][ihash].ihash = ihash
            tlist[current_idx][ihash].istopthree = count <= 3

    # lookupfolder = "multi_13_sc3_i10 multi_14_sc4_i10 multi_17_sr4_i10 multi_18_sr3_i10".split()
    lookupfolder = "multi_23_sc3_i10 multi_19_sr3_i10".split()
    printline = []
    header = "idx\t"

    for i in lookupfolder:
        header += "%s-top3\t%s-top6\t%s-topses\t" % (i,i,i)
        with open(path.join(i, "top.tsv")) as f:
            top3, top6, intopsession = 0.0, 0.0, 0.0
            current_idx = 0
            for line in f:
                if line.startswith('idx'):
                    continue
                if line.startswith('0'):
                    current_idx = 0
                    continue
                spline = line.split()
                ihash = spline[3]
                if int(spline[0]) == current_idx + 1:
                    # spline = current_idx + 1
                    if len(printline) < current_idx or (len(printline) == current_idx):
                        printline.append("%d\t%s\t%s\t%s" %(current_idx, top3, top6, intopsession))
                    else:
                        printline[current_idx] += "\t%s\t%s\t%s" %(top3, top6, intopsession)

                    top3, top6, intopsession = 0.0, 0.0, 0.0

                current_idx = int(spline[0])
                if ihash in tlist[current_idx].keys():
                    if tlist[current_idx][ihash].maxgain:
                        top6 += 1.0
                    if tlist[current_idx][ihash].istopthree:
                        top3 += 1.0
                    if tlist[current_idx][ihash].sessiongain:
                        intopsession += 1.0

    print header
    for p in printline:
        print p
if __name__ == "__main__":
    main()
