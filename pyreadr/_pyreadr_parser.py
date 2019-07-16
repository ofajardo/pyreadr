"""
@author: Otto Fajardo
"""
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd

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
        self.column_types = dict()
        self.columns = list()
        self.value_labels = dict()
        self.df = None
        self.timezone = timezone

    def convert_to_pandas_dataframe(self):
        """
        Coordinates all the necessary steps to convert the data collected from the parser to a pandas data frame.
        :return: a pandas data frame
        """
        self._consolidate_names()
        self._todf()
        self._covert_data()
        self._handle_value_labels()
        return self.df

    # Internal methods

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

        data = OrderedDict()
        for indx, column in enumerate(self.columns):
            colname = self.final_names[indx]
            data[colname] = column
        # print(data)
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
                # In addition np.bool(np.nan) evaluates to True, we have to take care of that
                na_index = df[colname] <= -2147483648
                if np.any(na_index):
                    if dtype.name == "INTEGER":
                        df[colname] = df[colname].astype(np.object)
                        df.loc[na_index, colname] = np.nan
                    elif dtype.name == "LOGICAL":
                        df[colname] = df[colname].astype('bool')
                        df[colname] = df[colname].astype(np.object)
                        df.loc[na_index, colname] = np.nan
                else:
                    if dtype.name == "LOGICAL":
                        df[colname] = df[colname].astype('bool')

    def _handle_value_labels(self):
        """
        R factors are represented as integer vectors, and their string equivalences are stored somewhere else. This
        method replaces the integers by the correspondent strings and transforms the data into a pandas category.
        """

        if self.value_labels:
            for colindx, labels in self.value_labels.items():
                colname = self.final_names[colindx]
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
