# py<span style="color:blue">r</span>ead<span style="color:blue">r</span>

A python package to read R RData and Rds files into 
pandas dataframes. It does not need to have R or other external
dependencies installed.
<br> 

This module is based on the [librdata](https://github.com/WizardMac/librdata) C library by 
[Evan Miller](https://www.evanmiller.org/) and the cython wrapper around 
[jamovi-readstat](https://github.com/jamovi/jamovi-readstat)
by the Jamovi team.

Detailed documentation on all available methods is in the 
[Module documentation](https://ofajardo.github.io/pyreadr/)

## Dependencies

The module depends on pandas, which you normally have installed if you got Anaconda (highly recommended.) If creating
a new conda or virtual environment or if you don't have it in your base installation, you will have to install it 
manually before using pyreadr. Pandas is not selected as a dependency in the pip package, as that would install 
pandas with pip and many people would prefer installing it with conda.

In order to compile from source, you will need a C compiler (see installation) and cython 
(version > 0.28).

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

## Basic Usage

Pass the path to a RData or Rds file to the function r_to_pandas. It will return a dictionary 
with object names as keys and pandas data frames as values.

For example, in order to read a RData file:

```python
import pyreadr

result = pyreadr.r_to_pandas('test_data/basic/two.RData')

# done! let's see what we got
print(result.keys()) # let's check what objects we got
df1 = result["df1"] # extract the pandas data frame for object df1
```

reading a Rds file is equally simple. Rds files have one single object, 
which you can access with the key None:

```python
import pyreadr

result = pyreadr.r_to_pandas('test_data/basic/one.Rds')

# done! let's see what we got
print(result.keys()) # let's check what objects we got: there is only None
df1 = result[None] # extract the pandas data frame for the only object available
```

Here there is a relation of all functions available. 
You can also check the [Module documentation](https://ofajardo.github.io/pyreadr/).

| Function in this package | Purpose |
| ------------------- | ----------- |
| r_to_pandas        | reads RData and Rds files |
| list_objects       | list objects and column names contained in RData or Rds file |

## Reading selected objects

You can use the argument use_objects of the function r_to_pandas to specify which objects
should be read. 

```python
import pyreadr

result = pyreadr.r_to_pandas('test_data/basic/two.RData', use_objects=["df1"])

# done! let's see what we got
print(result.keys()) # let's check what objects we got, now only df1 is listed
df1 = result["df1"] # extract the pandas data frame for object df1
```

## List objects and column names

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

## Timestamps and Timezones

R datetime objects (POSIXct and POSIXlt) are internally stored as UTC timestamps, and may have additional timezone
information if the user set it explicitly. librdata cannot retrieve that timezone information. If no timezone information
was set by the user R uses the local timezone for display. 

As timezone information is not available from librdata, pyreadr display UTC time by default, which will not match the
display in R. You can set explicitly some timezone (your local timezone for example) with the argument timezone for the
function r_to_pandas

```python
import pyreadr

result = pyreadr.r_to_pandas('test_data/basic/two.RData', timezone='CET')

```

if you would like to just use your local timezone as R does, you can 
get it with tzone (you need to install it first with pip) and pass the 
information to r_to_pandas:

```python

import tzlocal
import pyreadr

my_timezone = tzlocal.get_localzone().zone
result = pyreadr.r_to_pandas('test_data/basic/two.RData', timezone=my_timezone)

```


## What objects can be read

Data frames composed of character, numeric (double), integer, timestamp (POSIXct 
and POSIXlt), logical atomic vectors. Factors are also supported.

Tibbles are also supported.

Atomic vectors as described before can also be directly read, but as librdata
does not give the information of the type of object it parsed, therefore everything
is translated to a pandas data frame.

## Known limitations

* As explained before, altough atomic vectors as described before can also be directly read, but as librdata
does not give the information of the type of object it parsed, therefore everything
is translated to a pandas data frame.

* POSIXct and POSIXlt objects in R are stored internally as UTC timestamps and may have
in addition time zone information. librdata does not return time zone information and
thefore the display of the tiemstamps in R and in pandas may differ.

* Matrices and arrays are read, but librdata does not return information about
the dimensions, therefore those cannot be arranged properly multidimensional
numpy arrays. They are translated to pandas data frames with one single column.

* Lists are not read. Other objects are probably not either.

* Data frames with special values like arrays, matrices and other data frames
are not supported

