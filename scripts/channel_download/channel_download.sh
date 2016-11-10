#!/usr/bin/env bash

#if [ -z "$OUTPUT_DIR" ]; then
#    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
#    exit 1
#fi
#
#if [ -z "$EXPERIMENT_DIR" ]; then
#    echo 'ERROR: EXPERIMENT_DIR variable not found, are you running this script from within gumby?'
#    exit 1
#fi

#cd $OUTPUT_DIR

echo "Running post channel downloading..."

MERGE_TSV_FILE="all.tsv"

# find .log file and put them to output/data
mkdir -p data

for log in $(grep -H -r "Dispersy configured" | grep -v ^Binary | cut -d: -f1)
do
    thedir=`dirname $log`
    log_=${log##*/}
    # the name will be logname_localhost_nodenumber.log
    fname="${log_%.*}_`echo ${thedir} | tr /. _`.log"
    cp $log "data/$fname"

    tname="${fname%.*}.tsv"

    python channel_dl_parse.py data/$fname > data/$tname
done

tsvlist=$(find . -regex ".*\.tsv")
echo -e "ts\tihash\tactor\tul_speed\tdl_speed\tul_tot\tdl_tot\tprogress" > $MERGE_TSV_FILE.raw

for tsvs in $tsvlist
do
    tail -n +2 $tsvs >> $MERGE_TSV_FILE.raw
done
(head -n 1 $MERGE_TSV_FILE.raw && tail -n +2 $MERGE_TSV_FILE.raw | sort) > $MERGE_TSV_FILE.sorted

#R --no-save --quiet < "$EXPERIMENT_DIR"/scripts/install.r

# Create RData files for plotting from log files and crate image
#"$EXPERIMENT_DIR"/scripts/log2rdata.sh
