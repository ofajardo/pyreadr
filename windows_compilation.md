# Compiling pyreadr on windows

## Context

Python extensions can be compiled in two ways: using Microsoft Visual Studio with a version matching that of your 
python (see [here](https://blogs.msdn.microsoft.com/pythonengineering/2016/04/11/unable-to-find-vcvarsall-bat/),
 and [here](https://wiki.python.org/moin/WindowsCompilers)), or using MinGW, which is a mini-linux environment to 
cross-compile for windows, but using all the linux compiling toolchain.
Since Python 3.5, the recommended way is using Visual Studio, as Microsoft introduced changes in the compiler that are 
not 100% compatible with MINGW, actually it is recommended not to use mingw 
(see [this](https://stevedower.id.au/blog/building-for-python-3-5/) and [this](https://github.com/cython/cython/wiki/CythonExtensionsOnWindows)). 
However, librdata (the library that pyreadr wraps) is written in a way that depends on Posix (unix) libraries, 
and therefore cannot be compiled with Visual Studio, therefore, one must compile with MINGW. 

Initially I compiled using MVSC with the modified file from Jamovi. This however did not work well when trying to compile to use bzip2.
Now I am using m2w64-toolchain which is a conda package that makes the
process much easier (sources can be taken from librdata as is) and is compatible with Appveyor.

## Using m2w64-toolchain

pre-requisite:

* Install Anaconda or Miniconda and prepare the environment: run these commands on the Anaconda prompt and/or activate the conda 
environment properly

```
conda install setuptools pandas wheel pip libpython cython
conda install -c msys2 m2w64-toolchain
```

* compilation:

```
# set mingw32 as compiler
python setup.py config --compiler=mingw32
# Create a wheel. 
python setup.py bdist_wheel 
# install the wheel
pip install --pre --no-index --find-links dist/ pyreadr
# run tests (optional)
python.exe tests\test_basic.py
```

## Additional notes:

1. Dependency Walker does not work well anymore on Windows 10. Use [this one](https://github.com/lucasg/Dependencies) instead.
A very handy program is also [ListDlls](https://docs.microsoft.com/en-us/sysinternals/downloads/listdlls) that will list all dlls loaded by a 
process. This one however will not work if the dll is missing, so it helps only locating good loaded dlls.


