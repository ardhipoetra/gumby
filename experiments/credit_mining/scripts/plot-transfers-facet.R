#!/usr/bin/env Rscript
# © 2014 Mihai Capotă

# Plot pre-processed transfer evolutions recorded in TSV files

library(argparse)
library(extrafont)
library(fontcm)
library(ggplot2)
library(lubridate)
library(plyr)
library(scales)

parser <- ArgumentParser(description=
		"Plot pre-processed Tribler BoostingManager transfers")
parser$add_argument("transfers", help="logs used as input", nargs="*")
parser$add_argument("--output", help="name used as output")
parser$add_argument("--hours", help="maximum duration", type="integer",
		    default=1000)
parser$add_argument("--label", help="index of name used as output")
pargs <- parser$parse_args()

loadfonts()

load_and_return_all <- function(name) {
    load(name)
    all
}

all_transfers <- ldply(pargs$transfers, load_and_return_all)

start_ts <- min(all_transfers$ts)

transfers <- all_transfers[all_transfers$ts < start_ts + hours(pargs$hours),]

if (!is.null(pargs$label)) {
    log_split <- ldply(strsplit(transfers$log, "-"))
}
if (pargs$label == "1") {
    transfers$log <- factor(log_split$V1, level=c("seederratio", "creation",
						  "random"),
			    labels=c("SeederRatio", "SwarmAge", "Random"))
} else if (pargs$label == "2") {
    transfers$log <- factor(log_split$V2, level=c("300", "900", "1800"),
			    labels=c("5 min", "15 min", "30 min"))
} else if (pargs$label == "3") {
    transfers$log <- as.factor(log_split$V3)
}

pdf.options(family="Helvetica")

pdf(file=pargs$output, width=7, height=8)
ggplot(transfers) +
        geom_line(aes(x=ts, y=(sumu-sumd)/10^6+100)) +
	geom_line(aes(x=ts, y=(upload-download)/10^6+100, color=ihash),
		  alpha=0.5, size=2) +
        xlab("Timestamp") +
        ylab("Net upload gain [MB]") +
        scale_x_datetime(labels = date_format("%Y-%m-%d\n%H:%M")) +
	scale_y_log10() +
        theme(legend.position="none", panel.grid.minor = element_blank()) +
	annotation_logticks(sides='l') +
        facet_grid(log ~ .)
dev.off()
embed_fonts(pargs$output, options="-dPDFSETTINGS=/prepress")
