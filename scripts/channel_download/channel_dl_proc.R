#!/usr/bin/env Rscript

library(argparse)
library(plyr)
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
		    default="channel_dl_figure.pdf")
args <- parser$parse_args()


tt <- read.table(args$file, header=T)
tt$ts <- floor_time(as.POSIXct(tt$ts, "%Y%m%dT%H%M%OSZ", tz='UTC'), 2, "minute")

t.seeder <- filter(tt, (progress == 1.0 & dl_tot == 0))
t.seeder <- t.seeder[! (duplicated(t.seeder$ihash) & duplicated(t.seeder$actor)), c("ihash", "actor"), drop = FALSE]
t.download <- tt[! (t.seeder$ihash %in% tt$ihash & tt$actor %in% t.seeder$actor),]

t.clean <- filter(t.download, dl_speed != 0)
# download speed graph : MEAN
dlspeed.mean <- recast(t.clean, ts ~ ihash, measure.var=c("dl_speed"), fun.aggregate=mean)
dlspeed.mean.melt_na <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlspeed.mean <- zoo(dlspeed.mean, order.by=dlspeed.mean$ts)
#dlspeed.mean[is.na(dlspeed.mean)] <- 0
#dlspeed.mean <- na.locf(dlspeed.mean)
tmp <- as.data.frame(dlspeed.mean)
tmp$ts <- time(dlspeed.mean)
dlspeed.mean <- tmp
dlmean <- melt(dlspeed.mean, id.var="ts", variable.name="ihash", value.name="dl_speed")
dlmean <- transform(dlmean, dl_speed = as.numeric(dl_speed))
dlmean[is.na(dlmean)] <- 0

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
dlmax <- transform(dlmax, dl_speed = as.numeric(dl_speed))

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

# monkey patch
gain[is.na(gain)] <- 0

gain <- zoo(gain, order.by=gain$ts)
gain <- na.locf(gain)
tmp <- as.data.frame(gain)
tmp$ts <- time(gain)
gain <- tmp
gain.g <- melt(gain, id.var="ts", variable.name="ihash", value.name="gainvalue")
gain.g <- filter(gain.g, ! ihash == 'actor')
gain.g$gainvalue <- as.numeric(gain.g$gainvalue)
gain.g <- ddply(gain.g, c("ts", "ihash"), numcolwise(mean))

# piece availability
 dlist = list()
 for (i in levels(unique(tt$ihash))){
     tmp <- tt %>% filter(ihash == i, avail > 0, dl_tot == 0)
     dlist[[i]] <- tmp
 }
 tmp <- bind_rows(dlist)
 t.avail <- recast(tmp, ts ~ ihash, measure.var=c("avail"), fun.aggregate=mean)
 #t.avail.melt_na <- melt(t.avail, id.var="ts", variable.name="ihash", value.name="avail")
 t.avail <- zoo(t.avail, order.by = t.avail$ts)
 t.avail <- na.locf(t.avail)
 tmp <- as.data.frame(t.avail)
 tmp$ts <- time(t.avail)
 t.avail <- tmp

 p.avail <- melt(t.avail, id.var="ts", variable.name="ihash", value.name="avail")
 p.avail$avail <- as.numeric(p.avail$avail)


# node amount
ttx <- filter(tt, nodem != -1)
t.popularity <- recast(ttx, ts ~ ihash, measure.var=c("nodem"), fun.aggregate=mean)
t.popularity <- zoo(t.popularity, order.by = t.popularity$ts)
t.popularity <- na.locf(t.popularity)
tmp <- as.data.frame(t.popularity)
tmp$ts <- time(t.popularity)
t.popularity <- tmp

p.popularity <- melt(t.popularity, id.var="ts", variable.name="ihash", value.name="nodem")
p.popularity$nodem <- as.numeric(p.popularity$nodem)

# piece majority
dlist = list()
for (i in levels(unique(tt$ihash))){
    tmp <- tt %>% filter(ihash == i, piecem != -1, dl_tot == 0)
    dlist[[i]] <- tmp
}
tmp <- bind_rows(dlist)

t.piecerange <- recast(tmp, ts ~ ihash, measure.var=c("piecem"), fun.aggregate=mean)
t.piecerange <- zoo(t.piecerange, order.by = t.piecerange$ts)
t.piecerange <- na.locf(t.piecerange)
tmp <- as.data.frame(t.piecerange)
tmp$ts <- time(t.piecerange)
t.piecerange <- tmp

p.piecerange <- melt(t.piecerange, id.var="ts", variable.name="ihash", value.name="piecem")
p.piecerange$piecem <- as.numeric(p.piecerange$piecem)

# plots
pdf(file=args$output, width=18, height=8)
ggplot(dlmean) + geom_line(aes(x=ts, y=dl_speed, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom", axis.text.x = element_text(angle = 90, hjust = 1)) + ggtitle("Mean") + scale_x_datetime(breaks=seq(from = min(dlmean$ts), to = max(dlmean$ts), by = 3600)) + scale_y_continuous(limits=c(0,350))
ggplot(dlmax) + geom_line(aes(x=ts, y=dl_speed, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom") + ggtitle("Max") + scale_x_datetime(breaks=seq(from = min(dlmax$ts), to = max(dlmax$ts), by = 3600)) + scale_y_continuous(limits=c(0,400))
ggplot(pmc, aes(x=ts, y=amount, color=ihash, group=ihash, alpha=0.5), size=2) + geom_line() + theme(legend.position="bottom") + ggtitle("Max peer where upload > downloaded") + scale_x_datetime(breaks=seq(from = min(pmc$ts), to = max(pmc$ts), by = 3600))
ggplot(gain.g, aes(x=ts, y=gainvalue, color=ihash, alpha=0.5), size=2) + geom_line() + theme(legend.position="bottom") + ggtitle("Average upload gain (For peers)") + scale_x_datetime(breaks=seq(from = min(gain.g$ts), to = max(gain.g$ts), by = 3600))
ggplot(p.avail) + geom_line(aes(x=ts, y=avail, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom") + ggtitle("Availability") + scale_x_datetime(breaks=seq(from = min(p.avail$ts), to = max(p.avail$ts), by = 3600)) + scale_y_continuous(limits=c(0,1))
ggplot(p.popularity) + geom_line(aes(x=ts, y=nodem, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom") + ggtitle("Rarest piece node amount") + scale_x_datetime(breaks=seq(from = min(p.popularity$ts), to = max(p.popularity$ts), by = 3600))
ggplot(p.piecerange) + geom_line(aes(x=ts, y=piecem, color=ihash, alpha=0.5), size=2) + theme(legend.position="bottom") + ggtitle("Number of piece > than rarest piece") + scale_x_datetime(breaks=seq(from = min(p.piecerange$ts), to = max(p.piecerange$ts), by = 3600)) + scale_y_continuous(limits=c(0,500))
dev.off()
