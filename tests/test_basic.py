import unittest
import os

import pandas as pd
import numpy as np


class PyReadRBasic(unittest.TestCase):

    def setUp(self):

        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.parent_folder = os.path.split(self.script_folder)[0]
        self.data_folder = os.path.join(self.parent_folder, "test_data")
        self.basic_data_folder = os.path.join(self.data_folder, "basic")

        df1_dtypes = {'num': np.float64,
                      'int': np.object,
                      'char': np.object,
                      'fac': 'category',
                      'log': np.bool}
        df2_dtypes = {'num2': np.float64,
                      'int2': np.int32,
                      'char2': np.object,
                      'fac2': 'category',
                      'log2': np.bool}

        df1 = pd.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), dtype=df1_dtypes, parse_dates=[5, 6])
        df1.loc[pd.isna(df1['char']), 'char'] = ""
        df1.loc[df1['int'].notnull(), 'int'] = df1.loc[df1['int'].notnull(), 'int'].astype(np.int32)

        df2 = pd.read_csv(os.path.join(self.basic_data_folder, "df2.csv"), dtype=df2_dtypes)

        df3 = pd.read_csv(os.path.join(self.basic_data_folder, "df3.csv"), parse_dates=[0, 1])

        self.df1 = df1
        self.df2 = df2
        self.df3 = df3

        self.rdata_objects = ['df1', 'df2', 'char']
        self.rdata_objects_description = [{"object_name":"df1", "columns":['num', 'int', 'char', 'fac', 'log', 'tstamp1', 'tstamp2']},
        {"object_name":"df2", "columns":['num2', 'int2', 'char2', 'fac2', 'log2']},
        {"object_name":"char", "columns":[]}]
        self.use_objects = ["df1"]

    def test_rdata_basic(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.r_to_pandas(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        self.assertTrue(self.df1.equals(res['df1']))
        self.assertTrue(self.df2.equals(res['df2']))

    def test_rds_basic(self):

        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        res = pyreadr.r_to_pandas(rds_path)
        self.assertTrue(self.df1.equals(res[None]))

    def test_list_objects_rdata(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.list_objects(rdata_path)
        self.assertListEqual(self.rdata_objects_description, res)

    def test_rdata_use_objects(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.r_to_pandas(rdata_path, use_objects=self.use_objects)
        self.assertListEqual(list(res.keys()), self.use_objects)
        self.assertTrue(self.df1.equals(res['df1']))

    def test_rdata_tzone(self):

        rdata_path = os.path.join(self.basic_data_folder, "tzone.RData")
        res = pyreadr.r_to_pandas(rdata_path, timezone='CET')
        df3 = res["df3"]
        # there is no localization in the csv so, remove it for the comparison
        df3["tstampa"] = df3["tstampa"].dt.tz_localize(None)
        df3["tstampb"] = df3["tstampb"].dt.tz_localize(None)
        self.assertTrue(self.df3.equals(res['df3']))


if __name__ == '__main__':

    import sys

    if "--inplace" in sys.argv:
        script_folder = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
        sys.path.insert(0, script_folder)
        sys.argv.remove('--inplace')

    import pyreadr

    print("package location:", pyreadr.__file__)

    unittest.main()

