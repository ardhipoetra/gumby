#!/usr/bin/env python

import argparse
from collections import defaultdict, namedtuple, OrderedDict

class PriorityDown:
    def __init__(self):
        self.ts = "20161010T101010.100Z"
        self.rate_kb = 0
        self.infohash = "0" * 40
        self.type = 0

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()

    dl_index = []
    cm_index = []
    ihash_idx = {}
    total_cm = OrderedDict()

    tlist = defaultdict(lambda: PriorityDown())
    print "ihash\tts\tdl\ttype"
    with open(args.log) as fin:

        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue

            split_msg = message.split(" ")
            if len(split_msg) > 2:
                if split_msg[0] == "Find":
                    ihash_idx[split_msg[4][:5]] = split_msg[4]
                elif split_msg[0] == "Rate":
                    ihash = split_msg[1]
                    # tlist[ihash].ts = ts
                    # tlist[ihash].rate_kb = float(split_msg[3])
                    if ihash not in cm_index:
                        cm_index.append(ihash)

                    if ts not in total_cm.keys():
                        if len(total_cm.keys()) > 1:
                            print "%s\t%s\t%s\t%s\t" %("0"*40, total_cm.keys()[-1], total_cm[total_cm.keys()[-1]] , 0)
                        total_cm[ts] = float(split_msg[3])
                    else:
                        total_cm[ts] += float(split_msg[3])

                    tlist[ihash].type = - cm_index.index(ihash) - 1

                    print "%s\t%s\t%s\t%s\t" %(ihash, ts, float(split_msg[3]), - cm_index.index(ihash) - 1)
                elif len(split_msg) > 5 and split_msg[5] == "status=DLSTATUS_DOWNLOADING,":
                    shortihash = split_msg[1].split("=")[1][:-1]
                    ihash = ihash_idx.get(shortihash, shortihash)
                    # tlist[ihash].ts = ts
                    # tlist[ihash].rate_kb = float(split_msg[2])
                    if ihash not in dl_index:
                        dl_index.append(ihash)

                    tlist[ihash].type = dl_index.index(ihash) + 1

                    print "%s\t%s\t%s\t%s\t" %(ihash, ts, float(split_msg[2].split("=")[1][:-1]), dl_index.index(ihash) + 1)

        # print "%s\t%s\t%s\t%s\t" %("0"*40, total_cm.keys()[-1], total_cm[total_cm.keys()[-1]], 0)
    # print "ihash\tts\tdl\ttype"
    # for ihash, p_item in tlist.items():
    #     print "%s\t%s\t%s\t%s\t" %(ihash, p_item.ts, p_item.rate_kb, p_item.type)

if __name__ == "__main__":
    main()
