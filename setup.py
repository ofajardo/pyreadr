"""
    @author: Otto Fajardo

"""

import sys
import os
import re

import platform
import glob

from setuptools import setup, Extension
from Cython.Build import cythonize
import Cython

cyver = int(Cython.__version__.split(".")[0])
if cyver < 3:
    raise Exception("cython 3.0.0 or newer is required")

def is_conda():
    """
    Check if running in a conda/miniforge environment with GNU libiconv installed.
    The libiconv iconv.h renames iconv_open/iconv/iconv_close to libiconv_open/libiconv/libiconv_close,
    so when that header is picked up, libiconv must be linked. Without it, glibc's iconv is used.
    """
    if os.environ.get('CONDA_BUILD'):
        return False
    # in a venv created from a conda python, sys.prefix is the venv, but the headers (conda's iconv.h) still come
    # from the conda python in sys.base_prefix
    for prefix in {sys.prefix, sys.base_prefix}:
        if not os.path.exists(os.path.join(prefix, 'conda-meta')):
            continue
        header = os.path.join(prefix, 'include', 'iconv.h')
        if not os.path.isfile(header):
            continue
        with open(header, encoding='utf-8', errors='replace') as f:
            if re.search(r'^\s*#\s*define\s+iconv\s+libiconv\b', f.read(), re.MULTILINE):
                return True
    return False

librdata_source_files = []
librdata_source_files += sorted(glob.glob('pyreadr/libs/librdata/src/*.c'))
librdata_source_files += ['pyreadr/librdata.pyx']

library_dirs = []
libraries = []
include_dirs = []
extra_link_args = []
extra_compile_args = ['-DHAVE_ZLIB', '-DHAVE_BZIP2', '-DHAVE_LZMA']
exclude_package_data = {'pyreadr': ["*.dll", "*.lib"]}
include_package_data=True

if platform.system() == 'Darwin':
    libraries.append("iconv")
elif platform.system() == 'Windows':
    is64bit = sys.maxsize > 2 ** 32
    if not is64bit:
        msg = "Python 32 bit is not supported on Windows. Please use Python 64 bit"
        raise Exception(msg)
    include_dirs.append(".")
    include_dirs.append('pyreadr')
    include_dirs.append('pyreadr/libs/zlib')
    include_dirs.append('pyreadr/libs/bzip2')
    include_dirs.append('pyreadr/libs/lzma')
    include_dirs.append('pyreadr/libs/librdata')
    include_dirs.append('pyreadr/libs/iconv')
    library_dirs.append('pyreadr/libs/librdata')
    exclude_package_data = {}
    library_dirs.append("pyreadr")
    libraries.append('z')
    libraries.append('iconv')
    libraries.append('bz2')
    libraries.append('lzma')

elif platform.system() == 'Linux':
    libraries.append('z')
    libraries.append('bz2')
    libraries.append('lzma')
    PYREADR_LINK_ICONV = os.environ.get('PYREADR_LINK_ICONV', '').lower() not in ('', '0', 'false', 'no')
    if PYREADR_LINK_ICONV or is_conda():
        libraries.append('iconv')
else:
    raise RuntimeError('Unsupported OS')


librdata = Extension(
    'pyreadr.librdata',
    sources=librdata_source_files,
    library_dirs=library_dirs,
    libraries=libraries,
    include_dirs=include_dirs,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args)

long_description = """A Python package to read and write R RData and Rds files
into/from pandas or polars data frames. It does not need R or other external
dependencies installed.

It is based on the C library [librdata](https://github.com/WizardMac/librdata) and
a modified version of the Cython wrapper jamovi-readstat.

Please visit our project home page for more information:
https://github.com/ofajardo/pyreadr
"""

short_description = "Reads/writes R RData and Rds files into/from pandas or polars data frames."
setup(
    name='pyreadr',
    version='0.5.9',
    ext_modules=cythonize([librdata], force=True),
    packages=["pyreadr"],
    include_package_data=include_package_data,
    exclude_package_data=exclude_package_data,
    install_requires=['narwhals>=2.26.0', 'numpy'],
    # narwhals requires python 3.9
    python_requires=">=3.9",
    license="AGPL-3.0-or-later",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Cython",
        "Programming Language :: C",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Environment :: Console",
    ],
    description=short_description,
    author="Otto Fajardo",
    author_email="pleasecontactviagithub@notvalid.com",
    url="https://github.com/ofajardo/pyreadr",
    download_url="https://pypi.org/project/pyreadr/#files",
    long_description=long_description,
    long_description_content_type="text/markdown"
)
