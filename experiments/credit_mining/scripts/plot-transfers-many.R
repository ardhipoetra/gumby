#!/usr/bin/env Rscript
# © 2014 Mihai Capotă

# Plot many pre-processed transfer evolutions recorded in TSV files

library(argparse)
library(extrafont)
library(fontcm)
library(ggplot2)
library(lubridate)
library(plyr)
library(dplyr)
library(reshape2)
library(scales)
library(zoo)

parser <- ArgumentParser(description=
		"Plot pre-processed Tribler BoostingManager transfers")
parser$add_argument("transfers", help="logs used as input", nargs="*")
parser$add_argument("--output", help="name used as output")
parser$add_argument("--hours", help="maximum duration", type="integer",
		    default=1000)
pargs <- parser$parse_args()

loadfonts()

load_and_return_all <- function(name) {
    load(name)
    all
}

all_transfers <- ldply(pargs$transfers, load_and_return_all)
start_ts <- min(all_transfers$ts)
transfers <- all_transfers[all_transfers$ts < start_ts + hours(pargs$hours),]
t_grouped <- transfers %>% group_by(ts, log) %>% summarize(max_sumu=max(sumu),
							   max_sumd=max(sumd))
t_grouped$net_upload = t_grouped$max_sumu - t_grouped$max_sumd

# Data has NAs because of timestamp rounding. Replace NAs using LOCF
t_grouped <- recast(t_grouped, ts ~ log + variable,
		    measure.var=c("net_upload"))
t_zoo <- zoo(t_grouped, order.by=t_grouped$ts)
t_zoo <- na.locf(t_zoo)
tmp <- as.data.frame(t_zoo)
tmp$ts <- time(t_zoo)
t_grouped <- melt(tmp, id.var="ts")
t_grouped$value <- as.numeric(t_grouped$value)
t_grouped <- rename(t_grouped, log=variable, net_upload=value)

q10 <- function(x) {quantile(x, probs=0.1)}
q90 <- function(x) {quantile(x, probs=0.9)}

pdf.options(family="Helvetica")

pdf(file=pargs$output, width=7, height=4)
ggplot(t_grouped) +
	geom_line(aes(ts, net_upload/10^6, group=log, color=log), alpha=0.5) +
        theme(legend.position="none") +
	stat_summary(aes(ts, net_upload/10^6), geom="smooth", fun.ymin=q10,
		     fun.y=median, fun.ymax=q90, size=2, alpha=0.7) +
	scale_x_datetime(labels = date_format("%Y-%m-%d\n%H:%M")) +
        xlab("Timestamp") +
        ylab("Net upload gain [MB]")
dev.off()
embed_fonts(pargs$output, options="-dPDFSETTINGS=/prepress")
