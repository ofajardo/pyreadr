"""
    @author: Otto Fajardo

"""

import setuptools
import sys

import platform
import glob

from setuptools import setup, Extension
from Cython.Build import cythonize
import Cython

cyver = int(Cython.__version__.split(".")[0])
if cyver < 3:
    raise Exception("cython 3.0.0 or newer is required")

def is_ubuntu():
    """
    Checks if the current operating system is Ubuntu.
    
    This function is safe to run on any OS. It returns False if not on Linux
    or if the distribution is not Ubuntu.
    """
    if not sys.platform.startswith('linux'):
        return False
    
    try:
        with open('/etc/os-release', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('ID='):
                    # The value might have quotes, which we strip
                    distro_id = line.split('=', 1)[1].strip().strip('"\'')
                    if distro_id == 'ubuntu':
                        return True
    except FileNotFoundError:
        # If /etc/os-release doesn't exist, it's not a standard modern Linux.
        return False
        
    return False

librdata_source_files = []
librdata_source_files += glob.glob('pyreadr/libs/librdata/src/*.c')
librdata_source_files += ['pyreadr/librdata.pyx']

library_dirs = []
libraries = []
include_dirs = []
extra_link_args = []
extra_compile_args = ['-DHAVE_ZLIB', '-DHAVE_BZIP2', '-DHAVE_LZMA']
package_data ={'pryeadr': ["*.c", "*.pyx", "*.pxd"]}
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
    package_data ={'pryeadr': ["*.c", "*.pyx", "*.pxd", "*.dll", "*.lib"]}
    exclude_package_data = {}
    include_package_data=True
    library_dirs.append("pyreadr")
    libraries.append('z')
    libraries.append('iconv')
    libraries.append('bz2')
    libraries.append('lzma')
    
elif platform.system() == 'Linux':
    libraries.append('z')
    libraries.append('bz2')
    libraries.append('lzma')
    #extra_compile_args.append("--std=gnu99")
    if is_ubuntu():
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
    version='0.5.4',
    ext_modules=cythonize([librdata], force=True),
    packages=["pyreadr"],
    include_package_data=include_package_data,
    exclude_package_data=exclude_package_data,
    install_requires=['pandas>=1.2.0'],
    license="AGPL-3.0-or-later",
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
