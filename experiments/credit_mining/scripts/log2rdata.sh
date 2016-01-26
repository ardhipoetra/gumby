#!/bin/sh

# Create RData files for plotting from log files

set -e

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
DATA_DIR="$SCRIPT_DIR""/data"

for log in $(ls "$DATA_DIR"/*.log)
do
	tsv="$log".tsv
	"$SCRIPT_DIR"/log2transfertsv.py "$log" > "$tsv"
	"$SCRIPT_DIR"/plot-transfers.R --plotless "$tsv"
done

for i in $(seq 201 220)
do
	log="$DATA_DIR"/containers-good-5/jenkins@131.180.27.$i/boosting.log
	tsv="$DATA_DIR"/boosting-c$i.log.tsv
	"$SCRIPT_DIR"/log2transfertsv.py "$log" > "$tsv"
	"$SCRIPT_DIR"/plot-transfers.R --plotless "$tsv"
done
