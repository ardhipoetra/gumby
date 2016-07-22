#!/bin/sh

# Create RData files for plotting from log files
# 2014 Mihai C
# 2016 Ardhi P.P.H

set -e

if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
DATA_DIR="$OUTPUT_DIR/data"

echo "Looking for logs to generate RData files..."

cd $DATA_DIR

for log in $(ls)
do
	tsv="$log".tsv
	"$SCRIPT_DIR"/log2transfertsv.py "$log" > "$tsv"
	"$SCRIPT_DIR"/plot-transfers.R --plotless "$tsv"

	"$SCRIPT_DIR"/plot-transfers-facet.R --hours="50" --output="$log.pdf" --label=1 "$DATA_DIR/$tsv.RData"

	convert -resize 25% -density 300 -depth 8 -quality 85 "$log.pdf" "$log.png"
done

echo "Finish plotting"

#for i in $(seq 201 220)
#do
#	log="$DATA_DIR"/containers-good-5/jenkins@131.180.27.$i/boosting.log
#	tsv="$DATA_DIR"/boosting-c$i.log.tsv
#	"$SCRIPT_DIR"/log2transfertsv.py "$log" > "$tsv"
#	"$SCRIPT_DIR"/plot-transfers.R --plotless "$tsv"
#done
