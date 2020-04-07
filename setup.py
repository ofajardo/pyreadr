"""
    @author: Otto Fajardo

"""

import setuptools

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
extra_compile_args = ['-DHAVE_ZLIB']
data_files = []
data_folder = ""

if platform.system() == 'Darwin':
    libraries.append("iconv")
elif platform.system() == 'Windows':
    include_dirs.append(".")
    include_dirs.append('pyreadr')
    include_dirs.append('pyreadr/libs/zlib')
    include_dirs.append('pyreadr/libs/librdata')
    include_dirs.append('pyreadr/libs/iconv')
    library_dirs.append('pyreadr/libs/librdata')
    
    data_folder = "win_libs/64bit/"
    data_files = [("Lib/site-packages/pyreadr", [data_folder + "zlib.dll", data_folder + "iconv.dll",
                        data_folder + "charset.dll", data_folder + "iconv.lib"])]
                        
    library_dirs.append(data_folder)
    libraries.append('z')
    libraries.append('iconv')
    
elif platform.system() == 'Linux':
    libraries.append('z')
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
    version='0.2.7',
    ext_modules=cythonize([librdata], force=True),
    packages=["pyreadr"],
    include_package_data=True,
    data_files=data_files,
    install_requires=['pandas>0.24.0'],
    classifiers=[
        "Programming Language :: Python",
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
