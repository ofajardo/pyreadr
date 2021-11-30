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
