#!/bin/sh

# Plot all figures from RData files

set -e

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
DATA_DIR="$SCRIPT_DIR""/data"
FIGURES_DIR="$SCRIPT_DIR""/figures"

"$SCRIPT_DIR"/plot-transfers-facet.R --hours="50" --output="$FIGURES_DIR"/"policies-29.pdf" --label=1 "$DATA_DIR"/boosting-e*-b29-*.RData

"$SCRIPT_DIR"/plot-transfers-facet.R --hours="50" --output="$FIGURES_DIR"/"policies-30.pdf" --label=2 "$DATA_DIR"/boosting-e*-b30-*.RData

"$SCRIPT_DIR"/plot-transfers-facet.R --hours="50" --output="$FIGURES_DIR"/"policies-34.pdf" --label=3 "$DATA_DIR"/boosting-e*-b34-*.RData

"$SCRIPT_DIR"/plot-transfers-many.R --output="$FIGURES_DIR"/"containers-good.pdf" "$DATA_DIR"/boosting-c*.RData
