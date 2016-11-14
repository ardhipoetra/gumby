#!/usr/bin/env bash

if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

if [ -z "$EXPERIMENT_DIR" ]; then
    echo 'ERROR: EXPERIMENT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

cd $OUTPUT_DIR

echo "Running post credit mining..."

# find .log file and put them to output/data
mkdir -p data

for log in $(grep -H -r "Added source" | grep -v ^Binary | cut -d: -f1)
do
    thedir=`dirname $log`
    log_=${log##*/}
    cp $log "data/${log_%.*}_`echo ${thedir} | tr /. _`.log"
    echo "copying $log to data/"
done

R --no-save --quiet < "$EXPERIMENT_DIR"/scripts/install.r

# Create RData files for plotting from log files and crate image
"$EXPERIMENT_DIR"/scripts/log2rdata.sh

"$EXPERIMENT_DIR"/../../scripts/channel_download/channel_download.sh

#gumby/scripts/graph_data.sh
