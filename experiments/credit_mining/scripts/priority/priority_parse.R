#!/usr/bin/env Rscript

library(argparse)
library(dplyr)
library(ggplot2)
library(lubridate)
library(reshape2)
library(scales)
library(zoo)

# http://stackoverflow.com/a/23165334
floor_time <- function(x, k = 1, unit = c("second", "minute", "hour", "day",
                                          "week", "month", "year")) {
  require(lubridate)

  nmax <- NULL

  switch(unit, second = {nmax <- 60},
         minute = {nmax <- 60},
         hour = {nmax <- 24})

  cuts <- seq(from = 0, to = nmax - 1, by = k)
  new <- switch(unit,
                second = update(x, seconds = cuts[findInterval(second(x), cuts)]),
                minute = update(x, minutes = cuts[findInterval(minute(x), cuts)],
                                seconds = 0),
                hour = update(x, hours = cuts[findInterval(hour(x), cuts)],
                              minutes = 0, seconds = 0),
                day = update(x, hours = 0, minutes = 0, seconds = 0),
                week = update(x, wdays = 1, hours = 0, minutes = 0, seconds = 0),
                month = update(x, mdays = 1, hours = 0, minutes = 0, seconds = 0),
                year = update(x, ydays = 1, hours = 0, minutes = 0, seconds = 0))

  new
}

RobustMax <- function(x) {if (length(x)>0) max(x) else 0}

parser <- ArgumentParser(description="Plot priority download")
parser$add_argument("file", help="log used as input")
parser$add_argument("output", help="name used as output", nargs="?",
		    default="priority_figure.pdf")
args <- parser$parse_args()


tt <- read.table(args$file, header=T)
tt$ts <- floor_time(as.POSIXct(tt$ts, "%Y%m%dT%H%M%OSZ", tz='UTC'), 1, "minute")
 tt <- tt[!(tt$dl <= 0.0),]

dlspeed.mean <- recast(tt, ts ~ ihash, measure.var=c("dl"), fun.aggregate=mean)
dlspeed.mean.melt_na <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl")
dlspeed.mean <- zoo(dlspeed.mean, order.by=dlspeed.mean$ts)
tmp <- as.data.frame(dlspeed.mean)
tmp$ts <- time(dlspeed.mean)
dlspeed.mean <- tmp
dlmean <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl")
dlmean$dl <- as.numeric(dlmean$dl)
dlmean$type <- tt$type[match(dlmean$ihash, tt$ihash)]

dlspeed.max <- recast(tt, ts ~ ihash, measure.var=c("dl"), fun.aggregate=RobustMax)
dlspeed.max.melt_na <- melt(dlspeed.max, id.var="ts", variable.name="ihash", value.name="dl")
dlspeed.max <- zoo(dlspeed.max, order.by=dlspeed.max$ts)
dlspeed.max <- na.locf(dlspeed.max)
tmp <- as.data.frame(dlspeed.max)
tmp$ts <- time(dlspeed.max)
dlspeed.max <- tmp
dlmax <- melt(dlspeed.max, id.var="ts", variable.name="ihash", value.name="dl")
dlmax$dl <- as.numeric(dlmax$dl)
dlmax$type <- tt$type[match(dlmax$ihash, tt$ihash)]

dlmean.clean <- dlmean[!(dlmean$type < 0),]
dlmax.clean <- dlmax[!(dlmax$type < 0),]

dlmean.prio <- dlmean[!(dlmean$type < 1),]
dlmax.prio <- dlmax[!(dlmax$type < 1),]

# dlmax$variable <- reorder(dlmax$variable, dlmax$value)
# dlmax$variable <- factor(dlmax$variable, levels=rev(levels(dlmax$variable)))

pdf(file=paste("stacked", args$output, sep='_'), width=18, height=8)
ggplot(dlmean.clean) + geom_line(aes(x=ts, y=dl, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom", axis.text.x = element_text(angle = 90, hjust = 1)) + ggtitle("Mean") + scale_x_datetime(breaks=seq(from = min(dlmean$ts), to = max(dlmean$ts), by = 3600)) + scale_y_continuous(limits=c(0,350))
ggplot(dlmax[!(dlmax$type == 0),], aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Max")
if (nrow(subset(dlmax.clean, type == 0))) {
  ggplot(dlmax.clean, aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Aggregated Max")
}
ggplot(dlmax.prio, aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Priority Max")
ggplot(dlmean[!(dlmean$type == 0),], aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Mean")
if (nrow(subset(dlmean.clean, type == 0))) {
  ggplot(dlmean.clean, aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Aggregated Mean")
}

ggplot(dlmean.prio, aes(x=ts, y=dl, fill=ihash)) + geom_bar(stat="identity") + theme(legend.position="bottom") + ggtitle("Priority Mean")
dev.off()
