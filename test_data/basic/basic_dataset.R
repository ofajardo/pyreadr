# Produce RData and Rds for basic testing

num <- c(1,2,3, Inf,NA,NaN)
int <- as.integer(num)
char <- c("a", "b", "c", "a", "", NA)
fac <- c( "james", "cecil","zoe", "amber", NA, "rob")
log <- c(TRUE, TRUE, FALSE, TRUE, FALSE, NA)
tstamp1 <- as.POSIXlt(num, origin = "2017-02-03 08:00:00", tz = "GMT")
tstamp2 <- as.POSIXct(num, origin = "2017-02-03 08:00:00", tz = "GMT")

df1 <- data.frame(num, int, char, fac, log, tstamp1, tstamp2)
df1$char <- as.character(df1$char)

num2 <- c(4,5,6,3,5,6)
int2 <- as.integer(num2)
char2 <- c("d", "e", "f", "d", "e", "f")
fac2 <- c("d", "e", "f", "d", "e", "f")
log2 <- c(TRUE, TRUE, FALSE, TRUE, FALSE, TRUE)

df2 <- data.frame(num2, int2, char2, fac2, log2)
df2$char2 <- as.character(df2$char2)

mylist <- list("one"=1)

# save the RData file
save(df1, df2, char, mylist, file = "two.RData")
# Save the Rds file
saveRDS(df1, "one.Rds")

# Save as csv as well
df1$tstamp1 <- as.character(df1$tstamp1)
df1$tstamp2 <- as.character(df1$tstamp2)
write.csv(df1 ,file="df1.csv", row.names=FALSE)
write.csv(df2, file="df2.csv", row.names=FALSE)

# localized timezones
tstampa <- as.POSIXlt(num[1:3], origin = "2017-02-03 08:00:00", tz = "CET")
tstampb <- as.POSIXct(num[1:3], origin = "2017-02-03 08:00:00", tz = "CET")
df3 <- data.frame(tstampa, tstampb)
save(df3, file = "tzone.RData")
df3$tstampa <- as.character(df3$tstampa)
df3$tstampb <- as.character(df3$tstampb)
write.csv(df3 ,file="df3.csv", row.names=FALSE)

# dates
d <- as.Date(c("2019/07/14", "1794/01/01","1970/01/01", ""))
df <- data.frame(d)
saveRDS(df, "dates.rds")
save(df, file="dates.RData")
write.csv(df ,file="dates.csv", row.names=FALSE)

# bzip2 compression
# save the RData file
save(df1, df2, char, mylist, file = "two_bzip2.RData", compress = "bzip2")