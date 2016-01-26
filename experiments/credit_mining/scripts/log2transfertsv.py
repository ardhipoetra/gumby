#!/usr/bin/env python3
# coding=utf-8
# pylint: disable=invalid-name,too-many-locals
# © 2014 Mihai Capotă
"""Extract transfer information from log file into tsv file"""

import argparse

from collections import defaultdict, namedtuple

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("log", help="log used as input")
    args = argparser.parse_args()
    Transfer = namedtuple("Transfer", ["download", "upload", "ts"])
    TransferStatus = namedtuple("TransferStatus", ["transfer_history",
                                                   "last_transfer"])
    transfers = defaultdict(lambda: TransferStatus([Transfer(0, 0, 0)],
                                                   Transfer(0, 0, 0)))
    with open(args.log) as fin:
        for line in fin:
            try:
                ts, dummy_level, message = line.split("-", 2)
            except ValueError:
                continue
            if message.startswith("Status for"):
                p1, p2 = message.split(" : ")
                ihash = p1[-40:]
                new_download, new_upload = p2.split()
                new_download = int(new_download)
                new_upload = int(new_upload)
                transfer_history = transfers[ihash].transfer_history
                last_transfer = transfers[ihash].last_transfer
                if (new_download < last_transfer.download or
                        new_upload < last_transfer.upload):
                    download_diff = new_download
                    upload_diff = new_upload
                else:
                    download_diff = new_download - last_transfer.download
                    upload_diff = new_upload - last_transfer.upload
                transfer_history.append(
                    Transfer(transfer_history[-1].download + download_diff,
                             transfer_history[-1].upload + upload_diff, ts))
                transfers[ihash] = TransferStatus(transfer_history,
                                                  Transfer(new_download,
                                                           new_upload, ts))
    print("ihash", "download", "upload", "ts", sep="\t")
    for ihash, transfer_status in transfers.items():
        for transfer in transfer_status.transfer_history[1:]:
            print(ihash, transfer.download, transfer.upload, transfer.ts,
                  sep="\t")

if __name__ == "__main__":
    main()
