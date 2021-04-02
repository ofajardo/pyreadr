"""
    @author: Otto Fajardo

"""

import setuptools
import sys

import platform
import glob

from setuptools import setup, Extension
from Cython.Build import cythonize

librdata_source_files = []
librdata_source_files += glob.glob('pyreadr/libs/librdata/src/*.c')
librdata_source_files += ['pyreadr/librdata.pyx']

library_dirs = []
libraries = []
include_dirs = []
extra_link_args = []
extra_compile_args = ['-DHAVE_ZLIB', '-DHAVE_BZIP2', '-DHAVE_LZMA']
data_files = []
data_folder = ""

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
    
    data_folder = "win_libs/64bit/"
    data_files = [("Lib/site-packages/pyreadr", [data_folder + "zlib.dll", data_folder + "iconv.dll",
                        data_folder + "charset.dll", data_folder + "iconv.lib",
                        data_folder + "libbz2-1.dll",
                        data_folder + "liblzma-5.dll"])]
                        
    library_dirs.append(data_folder)
    libraries.append('z')
    libraries.append('iconv')
    libraries.append('bz2')
    libraries.append('lzma')
    
elif platform.system() == 'Linux':
    libraries.append('z')
    libraries.append('bz2')
    libraries.append('lzma')
    #extra_compile_args.append("--std=gnu99")
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

long_description = """ A Python package to read and write R RData and Rds files
into/from pandas data frames. It does not need to have R or other external
dependencies installed.
It is based on the C library librdata and
a modified version of the cython wrapper jamovi-readstat.<br>
Please visit out project home page for more information:<br>
https://github.com/ofajardo/pyreadr
"""

short_description = "Reads/writes R RData and Rds files into/from pandas data frames."

setup(
    name='pyreadr',
    version='0.4.1',
    ext_modules=cythonize([librdata], force=True),
    packages=["pyreadr"],
    include_package_data=True,
    data_files=data_files,
    install_requires=['pandas>0.24.0'],
    license="AGPLv3",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Cython",
        "Programming Language :: C",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Environment :: Console",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    ],
    description=short_description,
    author="Otto Fajardo",
    author_email="pleasecontactviagithub@notvalid.com",
    url="https://github.com/ofajardo/pyreadr",
    download_url="https://pypi.org/project/pyreadr/#files",
    long_description=long_description,
    long_description_content_type="text/markdown"
)
