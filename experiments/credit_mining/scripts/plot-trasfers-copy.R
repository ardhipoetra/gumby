#!/usr/bin/Rscript
# © 2014 Mihai Capotă

# Plot transfer evolution recorded in TSV file and store processed RData

library(argparse)
library(dplyr)
library(ggplot2)
library(lubridate)
library(reshape2)
library(scales)
library(zoo)

options(digits.secs = 3)

transfers$ts <- round_date(as.POSIXct(transfers$ts, "%Y%m%dT%H%M%OSZ",
				      tz="UTC"), "minute")

downloads <- recast(transfers, ts ~ ihash, measure.var=c("download"))
downloads_melt_na <- melt(downloads, id.var="ts", variable.name="ihash", value.name="download")
downloads <- zoo(downloads, order.by=downloads$ts)
downloads <- na.locf(downloads)
tmp <- as.data.frame(downloads)
tmp$ts <- time(downloads)
downloads <- tmp
moltend <- melt(downloads, id.var="ts")
moltend$value <- as.numeric(moltend$value)
sumd <- moltend %>% group_by(ts) %>% summarize(sumd=sum(value, na.rm=T))

uploads <- recast(transfers, ts ~ ihash, measure.var=c("upload"))
uploads_melt_na <- melt(uploads, id.var="ts", variable.name="ihash", value.name="upload")
uploads <- zoo(uploads, order.by=uploads$ts)
uploads <- na.locf(uploads)
tmp <- as.data.frame(uploads)
tmp$ts <- time(uploads)
uploads <- tmp
moltenu <- melt(uploads, id.var="ts")
moltenu$value <- as.numeric(moltenu$value)
sumu <- moltenu %>% group_by(ts) %>% summarize(sumu=sum(value, na.rm=T))

transfersum <- inner_join(sumu, sumd)
transfers_na <- inner_join(downloads_melt_na, uploads_melt_na)

all <- inner_join(transfers_na, transfersum)
log_name <- strsplit(args$transfers, "-b[[:alnum:]]+-")[[1]][2]
if (is.na(log_name)) {
    log_name <- strsplit(args$transfers, "-c")[[1]][2]
}
all$log <- strsplit(log_name, ".log.tsv")[[1]][1]
save(all, file=paste0(args$transfers, ".RData"))
# Does not save time zone
#write.table(all, file=paste0(args$transfers, ".table"), sep="\t")

if (args$plotless) {
    quit(save="no")
}

pdf(file=args$output, width=7, height=4)
ggplot(all) + geom_line(aes(x=ts, y=(sumu-sumd)/10^6)) + geom_line(aes(x=ts, y=(upload-download)/10^6, color=ihash, alpha=0.5), size=2) + xlab("Timestamp") + ylab("Net gain [MB]") + scale_x_datetime(labels = date_format("%Y-%m-%d\n%H:%M")) + theme(legend.position="none")
dev.off()

#ggplot(sumd) + geom_point(aes(x=ts, y=sumd/10^6))

#ggplot(sumu) + geom_point(aes(x=ts, y=sumu/10^6))

#ggplot(transfers) + geom_point(aes(x=ts, y=(upload-download)/10^6)) + facet_grid(ihash ~ .)

#pdf(file="figures/net_gain_per_hash.pdf", width=7, height=11)
#ggplot(transfers) + geom_line(aes(x=ts, y=(upload-download)/10^6), size=0.5) + facet_grid(ihash ~ .) + xlab("Timestamp") + ylab("Net gain [MB]") + scale_x_datetime(labels = date_format("%Y-%m-%d\n%H:%M")) + theme(legend.position="none")
#dev.off()
#
#pdf(file="figures/net_gain.pdf", width=7, height=4)
#ggplot(transfersum) + geom_line(aes(x=ts, y=(sumu-sumd)/10^6)) + xlab("Timestamp") + ylab("Net gain [MB]") + scale_x_datetime(labels = date_format("%Y-%m-%d\n%H:%M"))
#dev.off()
