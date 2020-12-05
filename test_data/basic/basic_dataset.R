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
df1$fac <- as.factor(df1$fac)

num2 <- c(4,5,6,3,5,6)
int2 <- as.integer(num2)
char2 <- c("d", "e", "f", "d", "e", "f")
fac2 <- c("d", "e", "f", "d", "e", "f")
log2 <- c(TRUE, TRUE, FALSE, TRUE, FALSE, TRUE)

df2 <- data.frame(num2, int2, char2, fac2, log2)
df2$char2 <- as.character(df2$char2)
df2$fac2 <- as.factor(df2$fac2)

mylist <- list("one"=1)

# save the RData file
save(df1, df2, char, mylist, file = "two.RData")
# Save the Rds file
saveRDS(df1, "one.Rds")

# dataframes with rownames
df1_rownames <- df1
row.names(df1_rownames) <- c("A", "B", "C", "D", "E", "F")
saveRDS(df1_rownames, "one_rownames.Rds")
save(df1_rownames, df2, char, mylist, file = "two_rownames.RData")

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
save(df1, df2, char, mylist, file = "two_xz.RData", compress = "xz")

# matrices
mat_simple <- matrix(1:12, nrow=4, ncol=3) 
saveRDS(mat_simple, "mat_simple.rds")
mat_simple_byrow <- matrix(1:12, nrow=4, ncol=3, byrow=TRUE) 
saveRDS(mat_simple_byrow, "mat_simple_byrow.rds")
matrownames <- c("A", "B", "C", "D")
matcolnames <- c("V1", "V2", "V3")
mat_rowcolnames <- matrix(1:12, nrow=4, ncol=3, dimnames = list(matrownames, matcolnames)) 
saveRDS(mat_rowcolnames, "mat_rowcolnames.rds")
mat_rownames <- matrix(1:12, nrow=4, ncol=3, dimnames = list(matrownames)) 
saveRDS(mat_rownames, "mat_rownames.rds")
mat_colnames <- matrix(1:12, nrow=4, ncol=3, dimnames = list(c(), matcolnames)) 
saveRDS(mat_colnames, "mat_colnames.rds")
samp <- data.frame(list("a"=c(1,1,1,1,0,0,0,0),"b"=c(0,1)))
samp_tab <- table(samp)
saveRDS(samp_tab, "table.rds")
array_simple <- array(data=1:12, dim=c(4,3)) 
saveRDS(array_simple, "array_simple.rds")
# errors
array_onlycol <- array(data=1:12, dim=c(0,12)) 
saveRDS(array_onlycol, "array_onlycol.rds")
array_onlyrow <- array(data=1:12, dim=c(12,0)) 
saveRDS(array_onlyrow, "array_onlyrow.rds")
array_onedim <- array(data=1:12, dim=c(12)) 
saveRDS(array_onlyrow, "array_onedim.rds")
array_3d <- array(data=1:36, dim=c(4,3,3)) 
saveRDS(array_3d, "array_3d.rds")
dim3 <- c("D1","D2","D3")
array_3d_named <- array(data=1:36, dim=c(4,3,3), dimnames = list(matrownames, matcolnames,dim3)) 
saveRDS(array_3d_named, "array_3d_named.rds")



