"""
@author: Otto Fajardo
"""
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd
# xray is needed for 3d arrays only
xray_available = False
try:
    import xarray as xr
    xray_available = True
except:
    pass

from .librdata import Parser
from .custom_errors import PyreadrError



class Table:
    """
    In librdata each object is parsed into a "table".
    This python object is passed to the Pyreadr parser and will collect all the data.
    Once the parsing is finished it has methods to convert to pandas data frame.
    """

    def __init__(self, timezone=None):

        self.name = None
        self.column_names = dict()
        self.column_names_special = dict()
        self.row_names = list() 
        self.column_types = dict()
        self.columns = list()
        self.value_labels = dict()
        self.df = None
        self.timezone = timezone
        self.dim = None
        self.dim_num = 0
        self.dim_names = list()
        self.dim_names_ready = list()
        self.arraylike_data = None

    def convert_to_pandas_dataframe(self):
        """
        Coordinates all the necessary steps to convert the data collected from the parser to a pandas data frame.
        :return: a pandas data frame
        """
        # we need to handle things differently depening wether the dim attribute is set
        if self.dim_num:
            self._arraylike_todf()
        else:
            self._dflike_todf()
        return self.df

    # Internal methods

    # methods for arraylike: array, matrix, table
    def _arraylike_todf(self):
        """
        Method to convert objects with the dim attribute set: matrices, 
        arrays and tables; also vectors if the user set the dim attribute
        explicitly.
        """
        self._arraylike_convert()
        self._arraylike_buildf()
        self._handle_value_labels()

    def _arraylike_convert(self):
        """
        convert the data to suitable types
        """
        if len(self.columns)>1:
            raise PyreadrError("matrix, array or table object with more than one vector!")

        dtype = self.column_types[0]
        if dtype.name == "CHARACTER":
            data = np.asarray(self.columns[0], dtype=object)
        else:
            data = np.asarray(self.columns[0])

        # apparently DATE arrays and matrices are not saved as date or datetimes but numeric
        # but if someone creates a vector and sets the dim attribute, we will get trough these.
        if dtype.name == "TIMESTAMP":
            # inf values do not make sense for timestamp
            data[data == np.inf] = np.nan
            data = pd.to_datetime(data, unit='s').values
            if self.timezone:
                data = data.dt.tz_localize('UTC').dt.tz_convert(self.timezone)
        elif dtype.name == "DATE":
            data[data == np.inf] = np.nan
            data = data.astype("datetime64[D]").astype(datetime)
        elif dtype.name == "LOGICAL" or dtype.name == "INTEGER":
            na_index = data <= -2147483648
            if np.any(na_index):
                if dtype.name == "INTEGER":
                    data = data.astype(object)
                    data[na_index] = np.nan
                elif dtype.name == "LOGICAL":
                    data = data.astype('bool')
                    data = data.astype(object)
                    data[na_index] = np.nan
            else:
                if dtype.name == "LOGICAL":
                    data = data.astype('bool')

        self.arraylike_data = data

    def _arraylike_buildf(self):
        """"
        Transform the one dimensional array to a dataframe with several rows and columns
        """
        data = self.arraylike_data
        dim = self.dim 
        if len(dim)>3:
            raise PyreadrError("Librdata currently supports arrays with up to 3 dimensions, you got %s dimensions" % str(len(dim)))
        dimtuple = tuple(dim.tolist())
        data = np.reshape(data, dimtuple, order='F')
        if self.dim_names:
            self.arrange_dimnames_arraylike()
            dim_names = self.dim_names_ready
            len_dim_names = len(dim_names)
            if self.dim_num<3:
                rownames = dim_names[0]
                colnames = None
                if len_dim_names>1:
                    colnames = dim_names[1]
                df = pd.DataFrame(data, columns=colnames, index=rownames)
            else:
                if not xray_available:
                    raise PyreadrError("Trying to read array with >2 dimensions, please install xarray!")
                df = xr.DataArray(data, dim_names)
        else:
            if self.dim_num<3:
                df = pd.DataFrame(data)
            else:
                if not xray_available:
                    raise PyreadrError("Trying to read array with >2 dimensions, please install xarray!")
                df = xr.DataArray(data)
        self.df = df

    def arrange_dimnames_arraylike(self):
        """
        Dimenion names are captured as a flat array, transform to a nested array for
        easier handling.
        """ 
        if self.dim_names:
            dimtuple = tuple(self.dim.tolist())
            dim_names = list()
            lendimnames = len(self.dim_names)
            allcnt = 0
            cnt = 0
            dimcnt = 0
            curdim = list()
            curdsize = dimtuple[dimcnt]
            for dname in self.dim_names:
                curdim.append(dname)
                cnt += 1
                allcnt += 1
                if cnt==curdsize:
                    if np.all(pd.isna(curdim)):
                        curdim = None
                    dim_names.append(curdim)
                    curdim = list()
                    cnt = 0
                    if allcnt < lendimnames:
                        dimcnt += 1
                        curdsize = dimtuple[dimcnt]
            self.dim_names_ready = dim_names

    # methods for data_frames
    # also vectors
    def _dflike_todf(self):
        """
        This one is for objects that do not have the dim attribute set: dataframes
        and atomic vectors. (but vectors can have the dim attribute in that case
        they go to the other method)
        """
        self._consolidate_names()
        self._todf()
        self._covert_data()
        self._handle_value_labels()
        self._handle_row_names()

    def _consolidate_names(self):
        """
        librdata may collect column (vector) names from two places, this method consolidates both.
        """

        final_names = dict()
        all_indexes = set(list(self.column_names.keys()) + list(self.column_names_special.keys()))
        for indx in all_indexes:
            normal = self.column_names.get(indx)
            special = self.column_names_special.get(indx)
            if normal and special:
                raise PyreadrError("Both normal and special names for column index %d" % indx)
            final = normal if normal else special
            final_names[indx] = final
        self.final_names = final_names

    def _todf(self):
        """
        Converts the data to a pandas data frame, which still needs some further processing.
        """

        # normal data frames
        data = OrderedDict()
        for indx, column in enumerate(self.columns):
            colname = self.final_names[indx]
            data[colname] = column
        df = pd.DataFrame.from_dict(data)
        self.df = df

    def _covert_data(self):
        """
        Downstream processing of the data inside the pandas data frame
        """

        df = self.df
        # handle timestamps
        for colindx, dtype in self.column_types.items():
            colname = self.final_names[colindx]
            if dtype.name == "TIMESTAMP":
                # inf values do not make sense for timestamp
                df.loc[df[colname] == np.inf, colname] = np.nan
                df[colname] = pd.to_datetime(df[colname], unit='s')
                if self.timezone:
                    df[colname] = df[colname].dt.tz_localize('UTC').dt.tz_convert(self.timezone)
            elif dtype.name == "DATE":
                df.loc[df[colname] == np.inf, colname] = np.nan
                df[colname] = df[colname].values.astype("datetime64[D]").astype(datetime)
            elif dtype.name == "LOGICAL" or dtype.name == "INTEGER":
                # iscategorical = value_labels.get(colindx)
                # if not iscategorical:
                # R NA values are represented by large negative integers
                # in pandas we only have np.nan to represent missing
                # values, therefore we need to change the data type to
                # object to be able to mix integers and the float nan
                # In addition bool(np.nan) evaluates to True, we have to take care of that
                na_index = df[colname] <= -2147483648
                if np.any(na_index):
                    if dtype.name == "INTEGER":
                        df[colname] = df[colname].astype(object)
                        df.loc[na_index, colname] = np.nan
                    elif dtype.name == "LOGICAL":
                        df[colname] = df[colname].astype('bool')
                        df[colname] = df[colname].astype(object)
                        df.loc[na_index, colname] = np.nan
                else:
                    if dtype.name == "LOGICAL":
                        df[colname] = df[colname].astype('bool')

    def _handle_row_names(self):
        """
        For dataframes, set rownames as index
        """
        if self.row_names:
            self.df['rownames'] = self.row_names
            self.df.set_index('rownames', inplace=True)

    # methods for both dim and no dim

    def _handle_value_labels(self):
        """
        R factors are represented as integer vectors, and their string equivalences are stored somewhere else. This
        method replaces the integers by the correspondent strings and transforms the data into a pandas category.
        """

        if self.value_labels:
            colnames = self.df.columns.tolist()
            if self.dim_num>0:
                if len(self.dim)>1:
                    dim = self.dim[1]
                else:
                    dim = 1
                indx_labels = [(x, self.value_labels[0]) for x in range(0, dim)]
            else:
               indx_labels = list(self.value_labels.items()) 
            for colindx, labels in indx_labels:
                colname = colnames[colindx]
                self.df = self.df.replace({colname: labels})
                self.df[colname] = self.df[colname].astype("category")


class PyreadrParser(Parser):
    """
    Parses the RData or Rds file using the parser defined in librdata.pyx which in turn uses the C API of librdata.
    """

    def __init__(self):

        self.column_index = -1
        self.table_index = -1
        self.table_names = list()
        self.table_data = list()
        self.current_table = None
        self.use_objects = None
        self.parse_current_table = True
        self.timezone = None

    def set_use_objects(self, use_objects):
        self.use_objects = use_objects

    def set_timezone(self, timezone):
        self.timezone = timezone

    def handle_table(self, name):
        """
        Every object in the file is called table, this method is evoked once per object.
        :param name: str: the name of the table
        """

        if (self.use_objects is None) or name in self.use_objects:

            self.parse_current_table = True
            self.table_index += 1
            self.column_index = -1

            table = Table()
            table.timezone = self.timezone
            table.name = name
            self.table_data.append(table)
            self.current_table = table

        else:
            self.parse_current_table = False

    def handle_column(self, name, data_type, data, count):
        """
        Evoked once per each column in the table.
        :param name: str: column name, may be None
        :param data_type: object of type DataType(Enum) (defined in librdata.pyx)
        :param data: a numpy array representing the data in R vector, may be empty
        :param count: int: number of elements in the array
        """
        if self.parse_current_table:
            self.column_index += 1
            self.current_table.column_names[self.column_index] = name
            self.current_table.column_types[self.column_index] = data_type
            if data is not None:
                self.current_table.columns.append(data)
            else:
                self.current_table.columns.append(list())

    def handle_column_name(self, name, index):
        """
        Some times name is None in handle column but it is recovered with this method.
        :param name: str: name of the column
        :param index: int: index of the column
        """
        if self.parse_current_table:
            self.current_table.column_names_special[index] = name

    def handle_dim(self, name, data_type, data, count):
        """
        Evoked once to retrieve the number of dimensions
        :param name: str: column name, may be None
        :param data_type: object of type DataType(Enum) (defined in librdata.pyx)
        :param data: a numpy array representing the number of dimensions
        :param count: int: number of elements in the array
        """
        if self.parse_current_table:
            self.current_table.dim = data
            self.current_table.dim_num = count

    def handle_dim_name(self, name, index):
        """
        Get one dimension name, one at a time, for matrices, arrays, tables.
        :param name: str: name of the dimension
        :param index: int: index of the dimension
        """
        if self.parse_current_table:
            self.current_table.dim_names.append(name)

    def handle_row_name(self, name, index):
        """
        Handles R dataframe's rownames
        :param name: str: name of the row
        :param index: int: index of the row
        """
        if self.parse_current_table:
            #self.current_table.row_names[index] = name
            self.current_table.row_names.append(name)

    def handle_text_value(self, name, index):
        """
        For character vectors this will be called once per row and will retrieve the string value for that row.
        :param name: str: string value for the row
        :param index: int: index of the row
        :return:
        """
        if self.parse_current_table:
            self.current_table.columns[self.column_index].append(name)

    def handle_value_label(self, name, index):
        """
        Factors are represented as integer vectors.
        For factors, this method is called before reading the integer data in the Factor column with handle_column.
        and will give all the string
        values correspondent to the integer values.
        :param name: str: string value
        :param index: int: integer value
        :return:
        """
        if self.parse_current_table:
            curindx = self.column_index + 1
            curlabels = self.current_table.value_labels.get(curindx)
            if curlabels:
                curlabels[index+1] = name
            else:
                curlabels = {index+1: name}
            self.current_table.value_labels[curindx] = curlabels


class ListObjectsParser(Parser):
    """
    Specialized parser to only retrieve the R objects in the file and their columns
    """

    def __init__(self):

        self.object_list = list()
        self.current_table = -1
        self.parse_current_table = False

    def handle_table(self, name):
        """
        Every object in the file is called table, this method is evoked once per object.
        :param name: str: the name of the table
        """
        curobject = {"object_name": name, "columns": list()}
        self.object_list.append(curobject)
        self.current_table += 1

    def handle_column_name(self, name, index):
        """
        Some times name is None in handle column but it is recovered with this method.
        :param name: str: name of the column
        :param index: int: index of the column
        """
        self.object_list[self.current_table]["columns"].append(name)
