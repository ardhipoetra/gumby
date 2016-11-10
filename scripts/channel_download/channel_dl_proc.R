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

# download speed graph : MEAN
dlspeed.mean <- recast(tt, ts ~ ihash, measure.var=c("dl_speed"), fun.aggregate=mean)
dlspeed.mean.melt_na <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlspeed.mean <- zoo(dlspeed.mean, order.by=dlspeed.mean$ts)
dlspeed.mean <- na.locf(dlspeed.mean)
tmp <- as.data.frame(dlspeed.mean)
tmp$ts <- time(dlspeed.mean)
dlspeed.mean <- tmp
dlmean <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlmean$dl_speed <- as.numeric(dlmean$dl_dl_speed)

# download speed graph : MAX
dlspeed.max <- recast(tt, ts ~ ihash, measure.var=c("dl_speed"), fun.aggregate=RobustMax)
dlspeed.max.melt_na <- melt(dlspeed.max, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlspeed.max <- zoo(dlspeed.max, order.by=dlspeed.max$ts)
dlspeed.max <- na.locf(dlspeed.max)
tmp <- as.data.frame(dlspeed.max)
tmp$ts <- time(dlspeed.max)
dlspeed.max <- tmp
dlmax <- melt(dlspeed.max, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlmax$dl_speed <- as.numeric(dlmax$dl_speed)

# number peer where upload > dl
tt$pos <- as.numeric(tt$ul_tot > tt$dl_tot)
posit.max <- recast(tt, ts + actor ~ ihash, measure.var=c("pos"), fun.aggregate=RobustMax)
posit.max.clean <- ddply(posit.max, ("ts"), numcolwise(sum))
posit.max.clean <- zoo(posit.max.clean, order.by=posit.max.clean$ts)
tmp <- as.data.frame(posit.max.clean)
tmp$ts <- time(posit.max.clean)
posit.max.clean <- tmp
pmc <- melt(posit.max.clean, id.var="ts", variable.name="ihash", value.name="amount")

# gain
t.seeder <- filter(tt, (progress == 1.0 & dl_tot == 0))
t.seeder <- t.seeder[! (duplicated(t.seeder$ihash) & duplicated(t.seeder$actor)), c("ihash", "actor"), drop = FALSE]

t.download <- tt[! (t.seeder$ihash %in% tt$ihash & tt$actor %in% t.seeder$actor),]

t.download$gain <- t.download$ul_tot - t.download$dl_tot
gain <- recast(t.download, ts + actor ~ ihash, measure.var=c("gain"), fun.aggregate=mean)
gain_na <- melt(gain, id.var=c("ts", "actor"), variable.name = "ihash", value.name = "avg_gain")

gain <- zoo(gain, order.by=gain$ts)
gain <- na.locf(gain)
tmp <- as.data.frame(gain)
tmp$ts <- time(gain)
gain <- tmp

# monkey patch
gain[is.na(gain)] <- 0

gain.g <- melt(gain, id.var="ts", variable.name="ihash", value.name="gainvalue")
gain.g <- filter(gain.g, ! ihash == 'actor')
gain.g$gainvalue <- as.numeric(gain.g$gainvalue)
gain.g <- ddply(gain.g, c("ts", "ihash"), numcolwise(mean))

# plots
ggplot(dlmean) + geom_line(aes(x=ts, y=dl_speed, color=ihash)) + theme(legend.position="bottom") + ggtitle("Mean")
ggplot(dlmax) + geom_line(aes(x=ts, y=dl_speed, color=ihash)) + theme(legend.position="bottom") + ggtitle("Max")
ggplot(pmc, aes(x=ts, y=amount, color=ihash, group=ihash)) + geom_line() + theme(legend.position="bottom") + ggtitle("Max peer where upload > downloaded")
ggplot(gain.g, aes(x=ts, y=gainvalue, color=ihash, group=ihash)) + geom_line() + theme(legend.position="bottom") + ggtitle("Average upload gain")