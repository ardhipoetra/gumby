#!/usr/bin/env Rscript

library(lubridate)
library(argparse)
library(dplyr)
library(plotrix)
library(ggplot2)

parser <- ArgumentParser(description="Plot Predownload peers")
parser$add_argument("file", help="log used as input")
parser$add_argument("predown", help="predown.tsv used as input", default="predown.tsv")
parser$add_argument("output", help="name used as output", nargs="?",
		    default="peers.pdf")
args <- parser$parse_args()


tt <- read.table(args$file, header=T)
tz <- read.table(args$predown, header=T)
tz <- filter(tz, length > 0.0)
tt <- filter(tt, ihash %in% tz$ihash)

tt1 <- filter(tt, tt$type == 1)
tt1.clean <- filter(tt1, tt1$peers != 0)

tt2 <- filter(tt, tt$type == 2)
tt2.clean <- filter(tt2, tt2$peers != 0)
#tt2.clean <- filter(tt2.clean, ihash %in% tt1.clean$ihash)


t.cut.sequence = c(1,2,3,4,5,10,15,20,Inf)
t.cut.breaks = 0:(length(t.cut.sequence)-1)

t.cut1 <- cut(tt1.clean$peers, t.cut.sequence)
#hist(as.numeric(t.cut), breaks=t.cut.breaks, xaxt='n', xlab='', main = "Predownload histogram")
#axis(1, at=t.cut.breaks, labels=replace(t.cut.sequence, t.cut.sequence==Inf, as.integer(max(tt1.clean$peers))), cex.axis=0.7)

t.cut2 <- cut(tt2.clean$peers, t.cut.sequence)
#hist(as.numeric(t.cut), breaks=t.cut.breaks, xaxt='n', xlab='', main = "Predownload histogram")
#axis(1, at=t.cut.breaks, labels=replace(t.cut.sequence, t.cut.sequence==Inf, as.integer(max(tt2.clean$peers))), cex.axis=0.7)

pdf(file=paste("hist", args$output, sep='_'))
multhist(list(as.numeric(t.cut1), as.numeric(t.cut2)), breaks=t.cut.breaks, main = "Peer amount", col=c("red", "blue"), names.arg = levels(t.cut1))
legend("topright", legend=c("After finish", "After delay"), fill=c("red", "blue"))
grid(ny=5, nx=NA)

#df <- data.frame(id=c("After finish", "After delay"), value=c(nrow(filter(tt1, tt1$peers == 0)), nrow(filter(tt2, tt2$peers == 0))))
#ggplot(data=df, aes(x=id, y=value, fill=id)) + geom_bar(stat="identity") + ggtitle("Number of 0 peers") + theme(legend.position="none")
dev.off()