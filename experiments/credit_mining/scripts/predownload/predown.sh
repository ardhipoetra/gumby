#!/bin/bash

if [ "$1" != "" ]; then
    echo "input $1"
else
    echo "input is empty?"
    exit
fi

~/git/thesis/gumby/experiments/credit_mining/scripts/predownload/predown_tsv.py $1 > predown.tsv
~/git/thesis/gumby/experiments/credit_mining/scripts/predownload/peer_parse.py $1 > peers.tsv
(head -n 1 peers.tsv && tail -n +2 peers.tsv | sort) > peers.tsv.sorted

~/git/thesis/gumby/experiments/credit_mining/scripts/predownload/predown_parse.R predown.tsv
convert -resize 25% -density 300 -depth 8 -quality 85 dist_predown.pdf dist_predown.png
convert -resize 25% -density 300 -depth 8 -quality 85 hist_predown.pdf hist_predown.png

~/git/thesis/gumby/experiments/credit_mining/scripts/predownload/peer_parse.R peers.tsv predown.tsv
convert -resize 25% -density 300 -depth 8 -quality 85 hist_peers.pdf hist_peers.png