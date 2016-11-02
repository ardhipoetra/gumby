#!/usr/bin/env python

import argparse
from collections import defaultdict

class Predown:
    def __init__(self):
        self.start_time = "20161010T101010.100Z"
        self.end_time = "20161010T101010.100Z"
        self.length = 0.0

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()

    predown = defaultdict(lambda: Predown())
    with open(args.log) as fin:

        for line in fin:
            line = line.splitlines()[0]
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue

            split_msg = message.split(" ")
            if len(split_msg) > 2 and split_msg[2] == "pre-downloading":
                if split_msg[1] == "finish" and len(split_msg) > 4:
                    predown[split_msg[0]].end_time = ts
                    predown[split_msg[0]].end_time = ts
                    predown[split_msg[0]].length = float(split_msg[4])
                if split_msg[1] == "start":
                    predown[split_msg[0]].start_time = ts
                if split_msg[1] == "timeout":
                    predown[split_msg[0]].length = -1.0

            #modify new input
            if len(split_msg) > 4 and split_msg[4] == "pre-downloading":
                if split_msg[3] == "attemps":
                    predown[split_msg[0]].length = -2.0
            if len(split_msg) > 3 and split_msg[3] == "short":
                ihash = split_msg[1]
                predown[ihash].length = -3.0

    print "ihash\tstart_time\tend_time\tlength"
    for ihash, p_item in predown.items():
        print "%s\t%s\t%s\t%s\t" %(ihash, p_item.start_time, p_item.end_time, p_item.length)

if __name__ == "__main__":
    main()
