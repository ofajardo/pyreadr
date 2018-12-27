"""
    @author: Otto Fajardo

"""

import setuptools

import platform
import glob

#from distutils.core import setup
#from distutils.extension import Extension
from setuptools import setup, Extension
from Cython.Build import cythonize


librdata_source_files = [ ]
librdata_source_files += glob.glob('pyreadr/libs/librdata/src/*.c')
print(librdata_source_files)
#librdata_source_files += glob.glob('src/*.c')
librdata_source_files += [ 'pyreadr/librdata.pyx' ]

library_dirs = [ ]
libraries = [ ]
include_dirs = [ ]
extra_link_args = [ ]
extra_compile_args = [ '-DHAVE_ZLIB' ]
data_files = []

if platform.system() == 'Darwin':
    pass
    #libraries.append('iconv')
elif platform.system() == 'Windows':
    include_dirs.append(".")
    include_dirs.append('pyreadr')
    include_dirs.append('pyreadr/libs/zlib')
    include_dirs.append('pyreadr/libs/librdata')
    library_dirs.append('pyreadr/libs/librdata')
    
    #libraries.append('libiconv-static')
    #libraries.append('libz-static')
    data_folder = "win_libs/64bit/"
    library_dirs.append(data_folder)
    data_files = [("",[data_folder + "zlib.dll"])]
    libraries.append('z')
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

long_description = """ A Python package to read R RData and Rds files
into pandas data frames. It does not need to have R or other external
dependencies installed.
It is based on the C library librdata and
the cython wrapper jamovi-readstat.<br>
Please visit out project home page for more information:<br>
https://github.com/ofajardo/pyreadr
"""

short_description = "Reads R RData and Rds files into pandas data frames."

setup(
    name='pyreadr',
    version='0.1.1',
    ext_modules=cythonize([librdata]),
    packages=["pyreadr"],
    include_package_data=True,
    data_files=data_files,
    install_requires=[],
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
    url="https://github.com/Roche/pyreadstat",
    download_url="https://github.com/Roche/pyreadstat/dist",
    long_description=long_description,
    long_description_content_type="text/markdown"
)
