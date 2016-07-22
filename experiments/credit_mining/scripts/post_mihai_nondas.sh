#!/usr/bin/env bash

if [ -z "$OUTPUT_DIR" ]; then
    echo 'ERROR: $OUTPUT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

if [ -z "$EXPERIMENT_DIR" ]; then
    echo 'ERROR: $EXPERIMENT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

if [ -z "$PROJECT_DIR" ]; then
    echo 'ERROR: $PROJECT_DIR variable not found, are you running this script from within gumby?'
    exit 1
fi

cd $PROJECT_DIR

echo "Running post credit mining for mihai's code..."

# find .log file and put them to output/data
mkdir -p "$OUTPUT_DIR/data"
cp tribler/boosting.log "$OUTPUT_DIR/data"

R --no-save --quiet < "$EXPERIMENT_DIR"/scripts/install.r

# Create RData files for plotting from log files and crate image
"$EXPERIMENT_DIR"/scripts/log2rdata.sh

#gumby/scripts/graph_data.sh