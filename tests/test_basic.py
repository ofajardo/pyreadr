"""
@author: Otto Fajardo
"""
import unittest
import os
import datetime
import warnings

import pandas as pd
import numpy as np

import pyreadr

class PyReadRBasic(unittest.TestCase):

    def setUp(self):

        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.parent_folder = os.path.split(self.script_folder)[0]
        self.data_folder = os.path.join(self.parent_folder, "test_data")
        self.basic_data_folder = os.path.join(self.data_folder, "basic")
        self.write_data_folder = os.path.join(self.data_folder, "write")

        df1_dtypes = {'num': np.float64,
                      'int': np.object,
                      'char': np.object,
                      'fac': 'category'}
                      
        df2_dtypes = {'num2': np.float64,
                      'int2': np.int32,
                      'char2': np.object,
                      'fac2': 'category'}
                      
        df1 = pd.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), dtype=df1_dtypes, parse_dates=[5, 6],
                          keep_default_na=False, na_values=["NA"])
        df1.loc[df1['int'].notnull(), 'int'] = df1.loc[df1['int'].notnull(), 'int'].astype(np.int32)

        df2 = pd.read_csv(os.path.join(self.basic_data_folder, "df2.csv"), dtype=df2_dtypes)

        df3 = pd.read_csv(os.path.join(self.basic_data_folder, "df3.csv"), parse_dates=[0, 1])

        self.df1 = df1
        self.df2 = df2
        self.df3 = df3

        self.rdata_objects = ['df1', 'df2', 'char']
        self.rdata_objects_description = [{"object_name": "df1", "columns": ['num', 'int', 'char', 'fac', 'log', 'tstamp1', 'tstamp2']},
            {"object_name": "df2", "columns": ['num2', 'int2', 'char2', 'fac2', 'log2']},
            {"object_name": "char", "columns": []}]
        self.use_objects = ["df1"]
        
        t = datetime.datetime(1960, 1, 1)
        sec = [np.NaN] * 8
        sec[7] = 2
        third = [np.NaN] * 8
        third[7] = 3
        third[0] = ""
        colnames = ["char", "int", "num", "log", "datetime", "date", "object", "categ"]
        df_out = pd.DataFrame([["a", 1, 2.2, True, t, t.date(), t.time(), 1], sec, third], columns=colnames)
        df_out["int"] = df_out["int"].astype("object")
        df_out.iloc[0, 1] = np.int32(df_out.iloc[0, 1])
        df_out["categ"] = df_out["categ"].astype("category")
        self.df_out = df_out

    def test_rdata_basic(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy comparing NaNs raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(self.df1.equals(res['df1']))
        self.assertTrue(self.df2.equals(res['df2']))

    def test_rds_basic(self):

        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        res = pyreadr.read_r(rds_path)
        self.assertTrue(self.df1.equals(res[None]))

    def test_rds_matrix(self):
        matrix = pd.DataFrame(np.array([[*range(1, 4)], [*range(4, 7)], [*range(7, 10)]]),
                              index=['X', 'Y', 'Z'],
                              columns=['A', 'B', 'C'])

        rds_path = os.path.join(self.basic_data_folder, "two.Rds")
        self.assertTrue(os.path.exists(rds_path))
        res = pyreadr.read_r(rds_path)

        self.assertTrue(matrix.equals(res[None]))

    def test_list_objects_rdata(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.list_objects(rdata_path)
        self.assertListEqual(self.rdata_objects_description, res)

    def test_rdata_use_objects(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(rdata_path, use_objects=self.use_objects)
        self.assertListEqual(list(res.keys()), self.use_objects)
        self.assertTrue(self.df1.equals(res['df1']))

    def test_rdata_tzone(self):

        rdata_path = os.path.join(self.basic_data_folder, "tzone.RData")
        res = pyreadr.read_r(rdata_path, timezone='CET')
        df3 = res["df3"]
        # there is no localization in the csv so, remove it for the comparison
        df3["tstampa"] = df3["tstampa"].dt.tz_localize(None)
        df3["tstampb"] = df3["tstampb"].dt.tz_localize(None)
        self.assertTrue(self.df3.equals(res['df3']))
        
    def test_write_rdata(self):
        
        path = os.path.join(self.write_data_folder, "test.RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, self.df_out)
        self.assertTrue(os.path.isfile(path))
        #res = pyreadr.read_r(path)
        #d = res["dataset"]
        #d['datetime'].loc[pd.isna(d['datetime'])] = pd.NaT
        #d['datetime'] = d['datetime'].to_timestamp()
        #d['categ'] = d['categ'].astype(int)
        #d['categ'] = d['categ'].astype('category')
        #self.assertTrue(self.df_out.equals(d))
        
    def test_write_rds(self):
        
        path = os.path.join(self.write_data_folder, "test.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out)
        self.assertTrue(os.path.isfile(path))
        

if __name__ == '__main__':

    import sys

    if "--inplace" in sys.argv:
        script_folder = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
        sys.path.insert(0, script_folder)
        sys.argv.remove('--inplace')

    import pyreadr

    print("package location:", pyreadr.__file__)

    # unittest.main(warnings="ignore") # this would ignore all kind of warnings (not good)
    unittest.main()
