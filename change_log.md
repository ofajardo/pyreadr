# 0.5.8 (github, pypi and conda: 2026.xx.xx)
* fixing list_objects raising AttributeError for data frames with row names (#120)
* adding numpy to install_requires in setup.py (#121)
* raising minimum narwhals version to 2.26.0 for polars 2 compatibility
* updated librdata to 321fd180f2b01e843a56e260cb68bdf19abaa4e2
* added encoding parameter to read_r and list_objects to read strings without encoding mark in an encoding other than the one declared in the file, solves #49
* added writing row names: a non-default pandas index is written as row names automatically, or any column with the new rownames_column argument of write_rdata and write_rds, fixes #68
* errors at the end of writing (in librdata's rdata_end_table/rdata_end_file) are now raised instead of silently ignored
* fixing writing data frames with zero rows (wrote an empty, invalid file) and zero columns (segmentation fault)
* fixing unsupported compression in write_rdata/write_rds: the error is now raised before writing, no temporary file is left behind
* fixing column types when reading empty columns: character columns with zero rows were float64 in pandas; in polars all empty columns, and character columns with only missing values, had the Null type. They now get the type of the R vector
* fixing reading factors: all R levels are now kept, in R order, including levels not present in the data (they were dropped and the categories were sorted alphabetically or by appearance). Breaking change for polars: factors are now read as pl.Enum with the R levels instead of pl.Categorical
* added writing factors: pandas categories and polars Categorical/Enum with string categories are now written as R factors (they were written as character vectors). Levels are the categories in their order (pandas, polars Enum) or the sorted values present in the data (polars Categorical)
* fixing segmentation fault reading factors with a NA level (addNA in R) and data frames with a NA column name. The NA level is dropped (pandas categories and polars Enum cannot have missing levels) and its values become missing
* numeric missing values (polars null, pandas pd.NA and None in object columns) are now written as R's NA instead of NaN. NaN (including pandas np.nan in float columns) is still written as NaN
* reading with polars: R's NaN in numeric columns is now read as NaN instead of null, only R's NA is null
* fixing writing pandas pd.NA: nullable Float64, Int64 and string columns with missing values and object columns with pd.NA raised TypeError, object columns with numbers or dates and pd.NA were written as the string "<NA>"
* added writing multiple data frames to a RData file: write_rdata accepts a dict (e.g. the output of read_r) with object names as keys and data frames as values; rownames_column can be a str or a dict per data frame. Possible since librdata fixed WizardMac/librdata#38
* all data frames are validated before writing, errors no longer leave a partially written file; fixed a memory leak (the librdata writer was never freed)
* fixing writing pandas object columns of integers, booleans, strings or dates with np.nan (for example R integer and logical columns with NA as read by pyreadr): they were written as character ("1", "nan", "True"), now they keep their type and NaN is written as NA. In object columns of floats NaN is still written as NaN
* faster writing (about 10x without compression, 3x with gzip): writes are buffered (librdata wrote every value with a separate system call) and the platform is checked once instead of for every value
* removing set_index(inplace=True) when reading row names, deprecated in pandas 3.1

# 0.5.7 (github, pypi and conda: 2026.09.28)
* Added support for polars via narwhals

# 0.5.6 (github, pypi and conda: 2026.04.13)
* fixing setup.py to skip linking iconv for conda builds, to fix conda packaging

# 0.5.5 (github, pypi and conda: 2026.04.13)
* Added env variable PYREADR_LINK_ICONV to force linking iconv on linux, solves #112
* Adding reading from file like objects (BytesIO), solves #55
* Added compresslevel parameter to write_rdata and write_rds for controlling gzip compression level (1-9) solves #115
* Increased gzip compression buffer size from 16KB to 1MB for better write performance solves #115
* replacing is_ubuntu with is_conda in setup.py
* adapting code to run on pandas 3
* adding github workflows

# 0.5.4 (github, pypi and conda: 2025.11.25)
* new pipeline to produce wheels based on cibuildwheel. For windows, mingw64 is used and 
   there is remediation, so that
  dlls are not needed in the same folder, but still needed there for compile and if conda would be 
  used for compiling.

# 0.5.3 (github, pypi and conda: 2025.03.04)
* renaming libbz2-1.dll to libbz2.dll, introducing lib files for zlib and bizp2 from 
conda-forge, in order to be able to compile with the new ming2w from conda-forge. bzip2 from 
[here](https://anaconda.org/conda-forge/bzip2/files/win-64/bzip2-1.0.8-h2466b09_7.conda) and zlib from 
[here](https://anaconda.org/conda-forge/zlib/files/win-64/zlib-1.3.1-h2466b09_2.conda)

# 0.5.2 (github, pypi and conda: 2024.07.30)
* introducing zlib.dll from conda forge libzlib and removing z*.lib files fixes #104 

# 0.5.1 (github, pypi and conda: 2024.07.25)
* fixing tests removing np.NaN to work with latest numpy version.
* updating zlib windows libs and h files to 1.3.1 fixes #100

# 0.5.0 (github, pypi and conda: 2023.10.23)
* fixing bug when writing an object column filtered so that the first row has not index 0

# 0.4.9 (github, pypi and conda: 2023.08.09)
* conda forge of 0.4.8 failed due to missing file in source distribution, adding
  file to manifest and releasing again, otherwise no changes.

# 0.4.8 (github, pypi: 2023.08.08, no conda)
* Updated code to work with Cython 3.0.0, earlier versions no longer supported.
* Including dll files in pyreadr folder and putting them as package data for windows,
  this solves issue #72. For unix no package data meaning no dll files but also no
  .c translated files in the wheel.

# 0.4.7 (github, pypi and conda: 2022.09.24)
* added toml file, fixes #88
* Added Citation

# 0.4.6 (github, pypi and conda: 2022.06.23)
* fixed signature #84

# 0.4.5 (github, pypi and conda: 2022.06.23)
* fixed numpy.float deprecation
* fixed truncation of files when writing on windows

# 0.4.4 (github, pypi and conda: 2021.12.02)
* Introducing new pandas data types Float64Dtype and Float32Dtype when writing.
  This requires pandas > 1.2.0. Python 3.6 taken out of wheels as there
  is no 1.2.0 version.

# 0.4.3 (github, pypi and conda: 2021.11.30)
* fixed bug when translating datetime to string when writing.

# 0.4.2 (github, pypi and conda: 2021.04.02)
*  Added support for pathlib, solves #70

# 0.4.1 (github, pypi and conda: 2021.04.02)
* removed warnings about np.bool and np.object

# 0.4.0 (github, pypi and conda: 2020.12.23)
* fixing seg fault with linux wheels #62

# 0.3.9 (github, pypi and conda: 2020.12.09)
* Implemented reading dataframe rownames as pandas index
* Implementing reading matrices, arrays, tables, solves #5.
* librdata source updated to commit 8623be2c626392028cd75c5fc45a90e1f70d97b9

# 0.3.8 (github, pypi and conda: 2020.11.15)
* Fixed sharing flags for opening files on windows

# 0.3.7 (github, pypi and conda: 2020.11.14)
* Added download\_file function
* using std=gnu99 from env_vars.sh in wheels to solve #56

# 0.3.6 (github, pypi and conda: 2020.10.22)
* Added license to setup.py

# 0.3.5 (github, pypi and conda: 2020.09.24)
* Solved #48

# 0.3.4 (github, pypi and conda: 2020.09.14)
* Updated librdata source to commit: 7188fa54b1894da24ceb8ccefd0a62113a38497c
  This improves reading of altrep objects
  and gives a better error when encountering S4 objects
  solves issues: #36, #35, #30

# 0.3.3 (github, pypi, and conda: 2020.09.04)
* Implemented reading files with lzma compression
* Not producing wheels for python 3.5 anymore

# 0.3.2 (github, pypi and conda: 2020.09.01)
* introduces gzip compression as an option (#41)

# 0.3.1 (github, pypi: 2020.08.30, conda: 2020.09.01)
* fixes bug #40

# 0.3.0 (github, pypi and conda: 2020.08.26)
* Removed the limit on column bytes length
* Reading dates vectors correctly (libradata issue #24.
* Librdata src updated to commit ba28c3ba1bb224901b873ce477282f61a51c567e 

# 0.2.9 (github, pypi and conda: 2020.05.20)
* corrected bug when writing file not being able to delete them with python on windows.
* raising error if trying to run setup.py on windows 32 bit.

# 0.2.8 (github, pypi and conda: 2020.04.23)
* reading files with bzip2 compression
* changed compilation on windows to mingw so that bzip can work (not working with mvsc).
  This also will help keeping the same source as librdata instead of manually doing the
  changes required for the sources to work with mvsc.

# 0.2.7 (github, pypi and conda: 2020.04.07)
* write is able to cope with mixed integer pandas types
* Windows dlls are now copied into the package folder instead of python root

# 0.2.6 (github, pypi and conda: 20120.02.26)
* expanding user for list objects and write functions

# 0.2.5 (release deleted from pypi)
* expanding user (~) when reading files, checking that file exists.

# 0.2.4 (github, pypi and conda: 2020.02.18)
* updated librdata to commit a29cba35bc167b2f60c90a7cafa5630fbe54b053
  to correct bug reported at the end of issue #3 

# 0.2.3 (github, pypi and conda: 2020.01.26)
* pandas added as install requirement

# 0.2.2 (github, pypi and conda: 2019.11.20)
* static linking iconv on mac.

# 0.2.1 (github, pypi and conda: 2019.07.16)
* librdata updated to 5987b140875eab59bf876ed18f2e5344484fe376 implemented the ability to read 
  vectors of type Date.

# 0.2.0 (github, pypi and conda: 2019.07.08)
* librdata source updated to 615dee09955b318ce128e0bfcc9d50aa3c9b7b7c 
  fixes #10 and reading files produced on windows with non ascii characters in content.
* Manifest file changed to include windows dll and those are taken from setup.py
  for unix, this fixes installation error messages on macos when using brew.

# 0.1.9 (github and pypi 2019.04.21,conda: )
* librdata source updated to b7ca1252b670d60a6e8d3c8ce6fcc8ab3b43d6ab
  fixes #3.

# 0.1.8 (github and pypi 2019.02.09, conda )
* setup.py fixed to build on conda-forge.
* conda forge package released

# 0.1.7 (github and pypi 2019.01.19)

* fixed distinguishing between empty string and NaN/NaT/None when writing. 
* librdata src updated to latest sources as 2019.01.19

# 0.1.6 (github and pypi 2019.01.06)

* fixed distinguishing between empty string and NA when reading. 

# 0.1.5 (github and pypi 2019.01.05)

* writing support added.

# 0.1.4 (github and pypi 2018.12.28)
* First stable release.
