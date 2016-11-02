#!/usr/bin/env Rscript

library(lubridate)
library(argparse)
library(dplyr)

parser <- ArgumentParser(description="Plot Predownload")
parser$add_argument("file", help="log used as input")
parser$add_argument("output", help="name used as output", nargs="?",
		    default="predown.pdf")
args <- parser$parse_args()


tt <- read.table(args$file, header=T)
tt$start_time <- round_date(as.POSIXct(tt$start_time, "%Y%m%dT%H%M%OSZ", tz='UTC'), "minute")
tt$end_time <- round_date(as.POSIXct(tt$end_time, "%Y%m%dT%H%M%OSZ", tz='UTC'), "minute")

t.clean <- filter(tt, tt$length > 0.0)

dirtynum <- length(tt$ihash) - length(t.clean$ihash)
timeoutnum <- dirtynum - nrow(filter(tt, tt$length == 0.0))
dirtynum <- dirtynum - timeoutnum

t.unfinish <- filter(tt, tt$length < 0.0)
t.unfinish.to <- filter(tt, tt$length == -1.0)
t.unfinish.sho <- filter(tt, tt$length == -3.0)
t.unfinish.att <- filter(tt, tt$length == -2.0)

dirtynum
timeoutnum

t.cut.sequence = c(seq(0, 299, 50), seq(300, 999, 100), 1000, 2000, 3000, Inf)
t.cut.breaks = 0:(length(t.cut.sequence)-1)

t.cut <- cut(t.clean$length, t.cut.sequence)

pdf(file=paste("hist", args$output, sep='_'))
hist(as.numeric(t.cut), breaks=t.cut.breaks, xaxt='n', xlab='', main = "Predownload histogram")
axis(1, at=t.cut.breaks, labels=replace(t.cut.sequence, t.cut.sequence==Inf, as.integer(max(t.clean$length))), cex.axis=0.7, las=2)
dev.off()

pdf(file=paste("dist", args$output, sep='_'), width=9, height=6)
pct <- round(c(length(t.clean$ihash), nrow(t.unfinish.to), nrow(t.unfinish.sho), nrow(t.unfinish.att))/sum(
c(length(t.clean$ihash), nrow(t.unfinish.to), nrow(t.unfinish.sho), nrow(t.unfinish.att)))*100)
lbls <- paste(c("Finished", "Timeout", "Short torrent", "Attemps"), pct) # add percents to labels
lbls <- paste(lbls,"%","(", c(length(t.clean$ihash), nrow(t.unfinish.to), nrow(t.unfinish.sho), nrow(t.unfinish.att)),")", sep="") # add % to labels
pie(c(length(t.clean$ihash), nrow(t.unfinish.to), nrow(t.unfinish.sho), nrow(t.unfinish.att)), labels=lbls, main="Finished download distribution", )
dev.off()
