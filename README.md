# py<span style="color:blue">r</span>ead<span style="color:blue">r</span>

A python package to read and write R RData and Rds files into/from 
pandas dataframes. It does not need to have R or other external
dependencies installed.
<br> 

This module is based on the [librdata](https://github.com/WizardMac/librdata) C library by 
[Evan Miller](https://www.evanmiller.org/) and a modified version of the cython wrapper around 
librdata
[jamovi-readstat](https://github.com/jamovi/jamovi-readstat)
by the [Jamovi](https://www.jamovi.org/) team.

Detailed documentation on all available methods is in the 
[Module documentation](https://ofajardo.github.io/pyreadr/)

If you would like to read SPSS, SAS or STATA files into python in an easy way,
take a look to [pyreadstat](https://github.com/Roche/pyreadstat), a wrapper
around the C library [ReadStat](https://github.com/WizardMac/ReadStat).

Moving from R to Python and fighting against indentation issues? Missing curly braces? Missing the <- operator
for assignment? Then try [PytwisteR](https://github.com/ofajardo/pytwister)! Python with a twist of R! 
(note: it works, but it's only a joke)

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
  * [Using pip](#using-pip)
  * [Using conda](#using-conda)
  * [From the latest sources](#from-the-latest-sources)
- [Usage](#usage)
  * [Basic Usage: reading files](#basic-usage--reading-files)
  * [Basic Usage: writing files](#basic-usage--writing-files)
  * [Reading selected objects](#reading-selected-objects)
  * [List objects and column names](#list-objects-and-column-names)
  * [Reading timestamps and timezones](#reading-timestamps-and-timezones)
  * [What objects can be read](#what-objects-can-be-read)
  * [More on writing files](#more-on-writing-files)
- [Known limitations](#known-limitations)
- [Change Log](#change-log)
- [People](#people)

## Dependencies

The module depends on pandas, which you normally have installed if you got Anaconda (highly recommended.) If creating
a new conda or virtual environment or if you don't have it in your base installation, pandas should get installed automatically.

In order to compile from source, you will need a C compiler (see installation) and cython 
(version >= 0.28).

librdata also depends on zlib; it was reported not to be installed on Lubuntu. If you face this problem intalling the 
library solves it.

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

We offer pre-compiled wheels for python 3.5, 3.6 and 3.7 for Windows,
linux and macOs.

### Using conda

The package is also available in [conda-forge](https://anaconda.org/conda-forge/pyreadr) 
for windows, mac and linux 64 bit, python 3.6 and 3.7. only.

In order to install:

```
conda install -c conda-forge pyreadr 
```

### From the latest sources

Download or clone the repo, open a command window and type:

```
python3 setup.py install
```

If you don't have admin privileges to the machine do:

```
python3 setup.py install --user
```

You can also install from the github repo directly (without cloning). Use the flag --user if necessary.

```
pip install git+https://github.com/ofajardo/pyreadr.git
```

You need a working C compiler and cython.

## Usage

### Basic Usage: reading files

Pass the path to a RData or Rds file to the function read_r. It will return a dictionary 
with object names as keys and pandas data frames as values.

For example, in order to read a RData file:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData')

# done! let's see what we got
print(result.keys()) # let's check what objects we got
df1 = result["df1"] # extract the pandas data frame for object df1
```

reading a Rds file is equally simple. Rds files have one single object, 
which you can access with the key None:

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/one.Rds')

# done! let's see what we got
print(result.keys()) # let's check what objects we got: there is only None
df1 = result[None] # extract the pandas data frame for the only object available
```

Here there is a relation of all functions available. 
You can also check the [Module documentation](https://ofajardo.github.io/pyreadr/).

| Function in this package | Purpose |
| ------------------- | ----------- |
| read_r        | reads RData and Rds files |
| list_objects  | list objects and column names contained in RData or Rds file |
| write_rdata   | writes RData files |
| write_rds     | writes Rds files   |

### Basic Usage: writing files

Pyreadr allows you to write one single pandas data frame into a single R dataframe
and store it into a RData or Rds file. Other python or R object types 
are not supported. Writing more than one object is not supported.


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

now you can check the result in R:

```r
load("test.RData")
print(dataset)

dataset2 <- readRDS("test.Rds")
print(dataset2)

```

### Reading selected objects

You can use the argument use_objects of the function read_r to specify which objects
should be read. 

```python
import pyreadr

result = pyreadr.read_r('test_data/basic/two.RData', use_objects=["df1"])

# done! let's see what we got
print(result.keys()) # let's check what objects we got, now only df1 is listed
df1 = result["df1"] # extract the pandas data frame for object df1
```

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

my_timezone = tzlocal.get_localzone().zone
result = pyreadr.read_r('test_data/basic/two.RData', timezone=my_timezone)

```

If you have control over the data in R, a good option to avoid all of this is to transform
the POSIX object to character, then transform it to a datetime in python.

When writing these kind of objects pyreadr transforms them to characters. Those can be easily
transformed back to POSIX with as.POSIXct/lt (see later).

### What objects can be read and written

Data frames composed of character, numeric (double), integer, timestamp (POSIXct 
and POSIXlt), date, logical atomic vectors. Factors are also supported.

Tibbles are also supported.

Atomic vectors as described before can also be directly read, but as librdata
does not give the information of the type of object it parsed everything
is translated to a pandas data frame.

Only single pandas data frames can be written into R data frames.

### More on writing files

For converting python/numpy types to R types the following rules are
followed:

| Python Type         | R Type    |
| ------------------- | --------- |
| np.int32 or lower   | integer   |
| np.int64, np.float  | numeric   |
| str                 | character |
| bool                | logical   |
| datetime, date      | character |
| category            | depends on the original dtype |
| any other object    | character |
| column all missing  | logical   |
| column with mixed types | character |


* datetime and date objects are translated to character to avoid problems
with timezones. These characters can be easily translated back to POSIXct/lt in R
using as.POSIXct/lt. The format of the datetimes/dates is prepared for this
but can be controlled with the arguments dateformat and datetimeformat 
for write_rdata and write_rds. Those arguments take python standard
formatting strings.

* Pandas categories are NOT translated to R factors. Instead the original
data type of the category is preserved and transformed according to the
rules. This is because R factors are integers and levels are always
strings, in pandas factors can be any type and leves any type as well, therefore
it is not always adecquate to coerce everything to the integer/character system.
In the other hand, pandas category level information is lost in the process.

* Any other object is transformed to a character using the str representation
of the object.

* Columns with mixed types are translated to character. This does not apply to column
cotaining np.nan, where the missing values are correctly translated.

* R integers are 32 bit. Therefore python 64 bit integer have to be 
promoted to numeric in order to fit.

* A pandas column containing only missing values is transformed to logical,
following R's behavior.

* librdata writes Numeric missing values as NaN instead of NA. In pandas we only have np.nan both as 
NaN and missing value representation, and it will always be written as NaN in R.

## Known limitations

* As explained before, although atomic vectors can also be directly read, as librdata
does not give the information of the type of object it parsed everything
is translated to a pandas data frame.

* POSIXct and POSIXlt objects in R are stored internally as UTC timestamps and may have
in addition time zone information. librdata does not return time zone information and
thefore the display of the tiemstamps in R and in pandas may differ.

* Matrices and arrays are read, but librdata does not return information about
the dimensions, therefore those cannot be arranged properly multidimensional
numpy arrays. They are translated to pandas data frames with one single column.

* Lists are not read.

* Objects that depend on non base R packages (Bioconductor for example) cannot be read.
The error code in this case is a bit obscure:

```python
"ValueError: Unable to read from file"
```

* Data frames with special values like arrays, matrices and other data frames
are not supported.

* The max size of a numeric vector is 2  **  32 bytes (4GB), meaning 2  **  30
elements for an Integer vector or 2  **  29 elements for a Double Vector. If
a vector in the dataframe is longer than this limit, a   
"Unable to allocate memory" error (see [this](https://github.com/ofajardo/pyreadr/issues/3) )
will arise.

* librdata first de-compresses the file in memory and then extracts the
data. That means you need more free RAM than the decompress file ocuppies
in memory. RData and Rds files are highly compressed: they can occupy
in memory easily 40 or even more times in memory as in disk. Take it into
account in case you get a "Unable to allocate memory" error (see [this](https://github.com/ofajardo/pyreadr/issues/3) )

* When writing numeric missing values are translated
to NaN instead of NA.

* Writing is supported only for a single pandas data frame to a single
R data frame. Other data types are not supported. Multiple data frames
for rdata files are not supported.

* RData and Rds files produced by R are (by default) compressed. Files produced
by pyreadr are not compressed and therefore pretty bulky in comparison. Pyreadr writing is a relative slow operation
compared to doint it in R.

* Cannot read RData or rds files in encodings other than utf-8.

Solutions to some of these limitations have been proposed in the upstream librdata [issues](https://github.com/WizardMac/librdata/issues) (points 1-4 are addressed by issue 12, point 5 by issue 16 and point 7 by issue 17). However there is no guarantee that these changes will be made and there are no timelines either. If you think it would be nice if these issues are solved, please express your support in the librdata issues.

## Change Log

A log with the changes for each version can be found [here](https://github.com/ofajardo/pyreadr/blob/write_support/change_log.md)

## People

[Otto Fajardo](https://github.com/ofajardo) - author, maintainer

[Jonathon Love](https://jona.thon.love/) - contributor (original cython wrapper from jamovi-readstat and msvc compatible librdata)
