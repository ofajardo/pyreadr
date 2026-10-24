# py<span style="color:blue">r</span>ead<span style="color:blue">r</span>

A python package to read and write R RData and Rds files into/from 
pandas or polars dataframes. It does not need to have R or other external
dependencies installed.
<br> 

**It can read mainly R data frames and tibbles. Also supports vectors, matrices, arrays and tables.
R lists and R S4 objects (such as those from Bioconductor) are not supported. Please read the
Known limitations section and the section on what objects can be read for more information.**
<br>

This package is based on the [librdata](https://github.com/WizardMac/librdata) C library by 
[Evan Miller](https://www.evanmiller.org/) and a modified version of the cython wrapper around 
librdata
[jamovi-readstat](https://github.com/jamovi/jamovi-readstat)
by the [Jamovi](https://www.jamovi.org/) team.

Detailed documentation on all available methods is in the 
[Module documentation](https://ofajardo.github.io/pyreadr/)

If you would like to read SPSS, SAS or STATA files into python in an easy way,
take a look at [pyreadstat](https://github.com/Roche/pyreadstat), a wrapper
around the C library [ReadStat](https://github.com/WizardMac/ReadStat).

If you would like to effortlessly produce beautiful summary tables from pandas 
dataframes, take a look at [pysummaries](https://github.com/Genentech/pysummaries)

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
  * [Using pip](#using-pip)
  * [Using conda](#using-conda)
  * [From the latest sources](#from-the-latest-sources)
- [Usage](#usage)
  * [Basic Usage: reading files](#basic-usage-reading-files)
  * [Basic Usage: writing files](#basic-usage-writing-files)
  * [Differences between pandas and polars output](#differences-between-pandas-and-polars-output)
  * [Reading from file-like objects](#reading-from-file-like-objects)
  * [Reading files from internet (download to disk)](#reading-files-from-internet-download-to-disk)
  * [Reading selected objects](#reading-selected-objects)
  * [Reading selected rows](#reading-selected-rows)
  * [List objects and column names](#list-objects-and-column-names)
  * [File metadata](#file-metadata)
  * [Reading timestamps and timezones](#reading-timestamps-and-timezones)
  * [Reading files with strings in other encodings](#reading-files-with-strings-in-other-encodings)
  * [What objects can be read](#what-objects-can-be-read-and-written)
  * [More on writing files](#more-on-writing-files)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [Change Log](#change-log)
- [People](#people)

## Dependencies

The package depends on narwhals and numpy, which get installed automatically. You will also need either pandas or polars
(or both) installed. When using `output_format="polars"` in `read_r`, you get polars DataFrames back. You can also
pass polars DataFrames directly to `write_rdata`/`write_rds`.

If you are reading 3D arrays, you will need to install xarray manually. This is not installed automatically as most users
won't need it.

In order to compile from source, you will need a C compiler (see installation) and cython 
(version >= 3.0).

librdata also depends on zlib, bzip2 and lzma; it was reported not to be installed on Lubuntu or docker base ubuntu
images. If you face this problem installing the libraries solves it.

## Installation

### Using pip

Probably the easiest way: from your conda, virtualenv or just base installation do:

```
pip install pyreadr
```

If you are running on a machine without admin rights, and you want to install against your base installation you can do:

```
pip install pyreadr --user
```

We offer pre-compiled wheels for Windows,
linux and macOs.

### Using conda

The package is also available in [conda-forge](https://anaconda.org/conda-forge/pyreadr) 
for windows, mac and linux 64 bit.

In order to install:

```
conda install -c conda-forge pyreadr 
```

### From the latest sources

Download or clone the repo, open a command window in the repo folder and type:

```
pip install .
```

If you don't have admin privileges to the machine do:

```
pip install . --user
```

You can also install from the github repo directly (without cloning). Use the flag --user if necessary.

```
pip install git+https://github.com/ofajardo/pyreadr.git
```

You need a working C compiler and cython. You may also need to install bzlib (on ubuntu install libbz2-dev).

On some Linux distros, iconv needs to be linked at compilation time, while in some other distros it must not 
be linked. Currently iconv linking happens automatically when building inside a conda/miniforge environment.
You can force iconv linking with the env variable PYREADR_LINK_ICONV=1 (set to 0, false or no to disable).

In order to run the tests against the installed package:

```
python tests/test_basic.py
python tests/test_narwhalified.py --backend=pandas
python tests/test_narwhalified.py --backend=polars
python tests/test_http_integration.py
``` 

You can also build and test in place, adding --inplace to each of the test commands above:

```
python setup.py build_ext --inplace
python tests/test_basic.py --inplace
```

## Usage

### Basic Usage: reading files

Pass the path to a RData or Rds file to the function read_r. It will return a dictionary 
with object names as keys and data frames as values (pandas by default, or polars with `output_format="polars"`).

For example, in order to read a RData file:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData')

# done! let's see what we got
print(result.keys()) # let's check what objects we got
df1 = result["df1"] # extract the data frame for object df1
```

reading a Rds file is equally simple. Rds files have one single object, 
which you can access with the key None:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/one.Rds')

# done! let's see what we got
print(result.keys()) # let's check what objects we got: there is only None
df1 = result[None] # extract the data frame for the only object available
```

You can also read directly into polars DataFrames:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData', output_format="polars")
df1 = result["df1"] # this is a polars DataFrame
```

Here there is a relation of all functions available. 
You can also check the [Module documentation](https://ofajardo.github.io/pyreadr/).

| Function in this package | Purpose |
| ------------------- | ----------- |
| read_r        | reads RData and Rds files |
| list_objects  | list objects and column names contained in RData or Rds file |
| read_metadata | file type, format version, compression and R versions of a RData or Rds file |
| download_file | download file from internet |
| write_rdata   | writes RData files |
| write_rds     | writes Rds files   |

### Basic Usage: writing files

Pyreadr allows you to write pandas or polars data frames into R dataframes
and store them into a RData (one or more data frames) or Rds (one data frame) file.
Other python or R object types are not supported.


```python
import pyreadr
import pandas as pd

# prepare a pandas dataframe
df = pd.DataFrame([["a",1],["b",2]], columns=["A", "B"])

# let's write into RData
# df_name is the name for the dataframe in R, by default dataset
pyreadr.write_rdata("test.RData", df, df_name="dataset")

# now let's write a Rds
pyreadr.write_rds("test.Rds", df)

# done!

```

Writing polars DataFrames works the same way:

```python
import pyreadr
import polars as pl

df = pl.DataFrame({"A": ["a", "b"], "B": [1, 2]})
pyreadr.write_rdata("test.RData", df, df_name="dataset")
pyreadr.write_rds("test.Rds", df)
```

To write several data frames into one RData file, pass a dict with the object names as keys.
The OrderedDict returned by read_r works as well, pandas and polars data frames can be mixed:

```python
pyreadr.write_rdata("test.RData", {"df1": df1, "df2": df2})

# copy some objects from one file to another
result = pyreadr.read_r("input.RData", use_objects=["df1", "df2"])
pyreadr.write_rdata("output.RData", result)
```

Now you can check the result in R:

```r
load("test.RData")
print(dataset)

dataset2 <- readRDS("test.Rds")
print(dataset2)

```

By default the resulting files will be uncompressed, you can activate gzip compression
by passing the option compress="gzip". This is useful in case you have big files.

You can also control the compression level with the `compresslevel` parameter (1-9).
The default is 9 (maximum compression, slowest). Lower values like 6 are significantly
faster with only a small increase in file size.

```python
import pyreadr
import pandas as pd

# prepare a pandas dataframe
df = pd.DataFrame([["a",1],["b",2]], columns=["A", "B"])

# write a compressed RData file
pyreadr.write_rdata("test.RData", df, df_name="dataset", compress="gzip")

# write a compressed Rds file
pyreadr.write_rds("test.Rds", df, compress="gzip")

# write with faster compression (level 6 instead of default 9)
pyreadr.write_rds("test.Rds", df, compress="gzip", compresslevel=6)

```

### Differences between pandas and polars output

When using `output_format="polars"`, the output differs from pandas in several ways:

| Aspect | pandas | polars |
| ------ | ------ | ------ |
| **Missing numeric values** | `NaN` (float) | `null` (R's `NaN` stays `NaN`) |
| **Missing integer values** | `object` dtype with `NaN` | `Int32` with `null` |
| **Missing logical values** | `object` dtype with `NaN` | `Boolean` with `null` |
| **Row names** | Set as DataFrame index | Added as a `rownames` string column |
| **Unnamed columns** | `None` as column name | Empty string `""` as column name |
| **Date columns** | Python `datetime.date` objects (`object` dtype) | Native `Date` dtype |
| **Factors** | `category` with all R levels | `Enum` with all R levels |

**Missing values:** R's `NA` maps to `NaN` in pandas and `null` in polars. This means
you use `pd.isna()` to check for missing values in pandas, and `.is_null()` in polars.
R's `NaN` in numeric data stays `NaN` in polars, so `NA` and `NaN` can be told apart
(`.is_null()` vs `.is_nan()`); in pandas both are `NaN`. In date and datetime columns
both are `null` in polars.

**Row names:** R data frames can have row names. In pandas these become the DataFrame
index. Since polars does not have an index, row names are added as a regular column
named `rownames`.

**Integer and logical columns with NA:** Polars natively supports nullable integer and
boolean types, so these columns keep their original types. In pandas, the presence of
`NaN` forces the column to `object` dtype.

### Reading from file-like objects

pyreadr can read directly from file-like objects instead of file paths. This is useful for:
- Reading from in-memory buffers (BytesIO)
- Streaming from remote sources without saving to disk

**Reading from a remote URL:**

```python
import io
import urllib.request
import pyreadr

url = "https://github.com/hadley/nycflights13/blob/main/data/airlines.rda?raw=true"
response = urllib.request.urlopen(url)
result = pyreadr.read_r(io.BytesIO(response.read()))
```

### Reading files from internet (download to disk)

Alternatively, pyreadr provides a function download_file to download a file from an url to disk:

```python
import pyreadr

url = "https://github.com/hadley/nycflights13/blob/main/data/airlines.rda?raw=true"
dst_path = "/some/path/on/disk/airlines.rda"
dst_path_again = pyreadr.download_file(url, dst_path)
res = pyreadr.read_r(dst_path)
```

As you see download_file returns the path where the file was written, therefore you can pass it
to pyreadr.read_r directly:

```python
import pyreadr

url = "https://github.com/hadley/nycflights13/blob/main/data/airlines.rda?raw=true"
dst_path = "/some/path/on/disk/airlines.rda"
res = pyreadr.read_r(pyreadr.download_file(url, dst_path))
```


### Reading selected objects

You can use the argument use_objects of the function read_r to specify which objects
should be read. 

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData', use_objects=["df1"])

# done! let's see what we got
print(result.keys()) # let's check what objects we got, now only df1 is listed
df1 = result["df1"] # extract the data frame for object df1
```

### Reading selected rows

With the arguments row_offset (rows to skip, 0 by default) and row_limit (maximal number of rows,
0 by default meaning all) of read_r you can read only some rows. They apply to every object read
(for matrices and arrays to the first dimension).

```python
import pyreadr

# rows 100 to 199 (counting from 0)
result = pyreadr.read_r('big_file.RData', row_offset=100, row_limit=100)
```

R stores data by column, so the columns are still read completely from the file, but only the
selected rows are kept: this is faster and needs much less memory than reading everything.

### List objects and column names

The function list_objects gives a dictionary with object names contained in the
RData or Rds file as keys and a list of column names as values.
It is not always possible to retrieve column names without reading the whole file
in those cases you would get None instead of a column name.

```python

import pyreadr

object_list = pyreadr.list_objects('test_data/basic/two.RData')

# done! let's see what we got
print(object_list) # let's check what objects we got and what columns those have

```

### File metadata

The function read_metadata reads only the header of a RData or Rds file (the data is not read,
so it is fast also for big files) and returns a dictionary with the file type, the
serialization format version, the compression and the version of R that wrote the file
as well as the minimal R version needed to read it back. It accepts paths and
file-like objects, as read_r.

```python
import pyreadr

meta = pyreadr.read_metadata('test_data/basic/meta_v3_xz.RData')
print(meta)
# {'file_type': 'RData', 'format_version': 3, 'compression': 'xz',
#  'writer_r_version': '4.3.3', 'min_reader_r_version': '3.5.0'}
```

Files written by pyreadr have format version 2, which can be read by any R version since 2.3.0.

### Reading timestamps and timezones

R Date objects are read as datetime.date objects.

R datetime objects (POSIXct and POSIXlt) are internally stored as UTC timestamps, and may have additional timezone
information if the user set it explicitly. If no timezone information
was set by the user R uses the local timezone for display. 

librdata cannot retrieve that timezone information, therefore pyreadr display UTC time by default, which will not match the
display in R. You can set explicitly some timezone (your local timezone for example) with the argument timezone for the
function read_r

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData', timezone='CET')

```

if you would like to just use your local timezone as R does, you can 
get it with tzlocal (you need to install it first with pip) and pass the 
information to read_r:

```python

import tzlocal
import pyreadr

my_timezone = tzlocal.get_localzone_name()
result = pyreadr.read_r('test_data/basic/two.RData', timezone=my_timezone)

```

If you have control over the data in R, a good option to avoid all of this is to transform
the POSIX object to character, then transform it to a datetime in python.

When writing these kind of objects pyreadr transforms them to characters. Those can be easily
transformed back to POSIX with as.POSIXct/lt (see later).

### Reading files with strings in other encodings

Strings are always returned as utf-8. R marks most strings with their encoding (utf-8 or latin1), and
those are converted automatically. Strings without a mark are assumed to be in the encoding declared in the file
(files saved with R >= 3.5) or utf-8 (older files). Sometimes that is not correct, for example
if the file was produced in a latin1 session but declares utf-8, and reading fails with a UnicodeDecodeError.
In that case you can set the encoding of those strings with the argument encoding (any encoding name
understood by iconv, for example "latin1" or "WINDOWS-1252"). It is available for read_r and list_objects:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/latin1_unflagged.RData', encoding="latin1")
objects = pyreadr.list_objects('test_data/basic/latin1_unflagged.RData', encoding="latin1")
```

### What objects can be read and written

Data frames composed of character, numeric (double), integer, timestamp (POSIXct 
and POSIXlt), date, logical atomic vectors. Factors are also supported: they are read
as pandas categories or polars Enum, keeping all the R levels in the R order (also levels
not present in the data). Ordered factors are read as unordered categories.

Tibbles are also supported.

Atomic vectors as described before can also be directly read and are 
translated to a data frame with one column. 

Matrices, arrays and tables are also read and translated to data frames
(because those objects in R can be named, and plain numpy arrays do not support
dimension names). The only exception is 3D arrays, which are translated to a
xarray DataArray (as neither pandas nor polars support more than 2 dimensions). This is also
the only time that an object different from a data frame is returned by read_r.

For 3D arrays, consider that python prints these in a different way as R does, but still
you are looking at the same array (see for example [here](https://rstudio.github.io/reticulate/articles/arrays.html#displaying-arrays) for an explanation.)

Only pandas or polars data frames can be written into R data frames (one per object; several
objects in a RData file).

Lists and S4 objects (such as those coming from Bioconductor) are not supported, they are skipped. Please read the Known limitations section for more
information.

### More on writing files

For converting python/numpy/polars types to R types the following rules are
followed:

| Python Type         | R Type    |
| ------------------- | --------- |
| np.int32 or lower   | integer   |
| np.int64, float     | numeric   |
| str                 | character |
| bool                | logical   |
| datetime, date      | character |
| category / Enum with string categories | factor |
| category with other categories | depends on the original dtype |
| any other object    | character |
| column all missing  | logical   |
| column with mixed types | character |


* datetime and date objects are translated to character to avoid problems
with timezones. These characters can be easily translated back to POSIXct/lt in R
using as.POSIXct/lt. The format of the datetimes/dates is prepared for this
but can be controlled with the arguments dateformat and datetimeformat 
for write_rdata and write_rds. Those arguments take python standard
formatting strings.

* Pandas categories and polars Categorical/Enum with string categories are translated to
R factors. For pandas categories and polars Enum the levels are the categories, in the same order,
including the ones not present in the data. Polars Categorical do not have levels of their own
(categories are shared by all columns), therefore the levels are the values present in the data,
sorted, as R's factor() does. Ordered categories are written as unordered factors.

* Pandas categories that are not strings are NOT translated to R factors, because R factor
levels are always strings. Instead the original data type of the categories is preserved and
transformed according to the rules; category level information is lost in the process.

* Any other object is transformed to a character using the str representation
of the object.

* Columns with mixed types are translated to character. This does not apply to columns
containing missing values (np.nan in pandas, null in polars), where the missing values
are correctly translated.

* R integers are 32 bit. Therefore python 64 bit integer have to be 
promoted to numeric in order to fit.

* A column containing only missing values is transformed to logical,
following R's behavior, if it has no declared type (pandas object column with None or pd.NA,
polars column of type Null). Columns with a declared type keep it (e.g. a string column
is written as character), and a pandas object column with only NaN as numeric NaN.

* Numeric missing values: polars null, pandas pd.NA (nullable types such as Float64 or Int64)
and None in object columns are written as R's NA. NaN is written as R's NaN, this includes the
np.nan of pandas float columns.

* Row names: the index of a pandas data frame is written as R row names, unless it is the
default RangeIndex (0, 1, 2 ...), in which case R gets its default row names (1, 2, 3 ...).
Alternatively, with the argument rownames_column you can write any column as row names
(this is the only option for polars, as polars has no index); that column is then
not written as a regular column. Row names are converted to strings and cannot contain
missing values or duplicates (R does not allow it). A pandas MultiIndex cannot be written as
row names.

```python
import pandas as pd
import pyreadr

df = pd.DataFrame({"id": ["a", "b", "c"], "x": [1.0, 2.0, 3.0]})
# the index becomes the row names
pyreadr.write_rds("test.rds", df.set_index("id"))
# same, using a column (works for polars too)
pyreadr.write_rds("test.rds", df, rownames_column="id")
```

When writing several data frames, rownames_column can be a string, applied to the data frames
that have that column, or a dict with the object names as keys to set it per data frame:

```python
pyreadr.write_rdata("test.RData", {"df1": df1, "df2": df2}, rownames_column={"df2": "id"})
```

## Known limitations

* POSIXct and POSIXlt objects in R are stored internally as UTC timestamps and may have
in addition time zone information. librdata does not return time zone information and
therefore the display of the timestamps in R and in python may differ.

* Librdata reads arrays with a maximum of 3 dimensions. If more dimensions are present
you will get an error. Please submit an issue if this is the case. 

* **Lists and S4 objects (for example from Bioconductor) are not read.** They are skipped: from a
RData file with other objects, these other objects are read. If nothing in the file can be read,
read_r returns an empty dictionary and gives a warning. Other kind of objects, including those
that depend on non base R packages, may not be readable either. The error in this case is:

```python
"pyreadr.custom_errors.LibrdataError: The file contains an unrecognized object"
```

* Data frames with special values like arrays, matrices, lists and other data frames
as columns are not supported.

* The whole data is read into memory. RData and Rds files are highly compressed: the data
can easily occupy 40 or even more times in memory than the file on disk. Take it into
account in case you get a "Unable to allocate memory" error (see [this](https://github.com/ofajardo/pyreadr/issues/3)).
With use_objects you can read only some objects of a RData file, and with row_offset and row_limit only some rows.

* Writing is supported only for pandas or polars data frames to R data frames. Other data
types are not supported. Rds files hold a single data frame.

* RData and Rds files produced by R are (by default) compressed. Files produced
by pyreadr are not compressed by default and therefore pretty bulky in comparison. You
can pass the option compress="gzip" to write_rds or write_rdata in order to activate 
gzip compression.

* Pyreadr writing is slower than doing it in R, especially for large data frames.

* Data frames written by pyreadr have two extra attributes, "datalabel" (the object name) and
"var.labels" (an empty string per column), added by librdata. They are harmless but visible in R
with attributes() or str().

* Data frames with duplicate column names cannot be written (R allows them, but pyreadr does not
support them).

Most of these limitations come from the underlying C library librdata. Solutions to some of them have been proposed in the upstream librdata [issues](https://github.com/WizardMac/librdata/issues), for example reading time zones and other attributes in [issue 12](https://github.com/WizardMac/librdata/issues/12). However there is no guarantee that these changes will be made and there are no timelines either. If you think it would be nice if these issues are solved, please express your support in the librdata issues.

## Contributing

Contributions are welcome! Please check the document [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## Change Log

A log with the changes for each version can be found [here](https://github.com/ofajardo/pyreadr/blob/master/change_log.md)

## People

[Otto Fajardo](https://github.com/ofajardo) - author, maintainer

[Jonathon Love](https://jona.thon.love/) - contributor (original cython wrapper from jamovi-readstat and msvc compatible librdata)

[deenes](https://github.com/deeenes) -  reading lzma compression

[Daniel M. Sullivan](https://www.danielmsullivan.com) - added license information to setup.py
