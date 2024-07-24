"""
@author: Otto Fajardo
"""
import unittest
import os
import datetime
import warnings
import shutil
from string import ascii_uppercase

import pandas as pd
import numpy as np
import xarray as xr

is_pathlib_available = False
try:
    from pathlib import Path
    is_pathlib_available = True
except:
    pass


class PyReadRBasic(unittest.TestCase):

    def setUp(self):

        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.parent_folder = os.path.split(self.script_folder)[0]
        self.data_folder = os.path.join(self.parent_folder, "test_data")
        self.basic_data_folder = os.path.join(self.data_folder, "basic")
        self.write_data_folder = os.path.join(self.data_folder, "write")

        df1_dtypes = {'num': np.float64,
                      'int': object,
                      'char': object,
                      'fac': 'category'}

        df1_tstamp_dtypes = {'num': np.float64,
                      'int': object,
                      'char': object,
                      'fac': 'category',
                      'tstamp1': str,
                      'tstamp2': str}
                      
        df2_dtypes = {'num2': np.float64,
                      'int2': np.int32,
                      'char2': object,
                      'fac2': 'category'}
                      
        df1 = pd.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), dtype=df1_dtypes, parse_dates=[5, 6],
                          keep_default_na=False, na_values=["NA"])
        df1.loc[df1['int'].notnull(), 'int'] = df1.loc[df1['int'].notnull(), 'int'].astype(np.int32)
        
        df1_tstamp = pd.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), dtype=df1_tstamp_dtypes,
                          keep_default_na=False, na_values=["NA"])
        df1_tstamp.loc[df1['int'].notnull(), 'int'] = df1.loc[df1['int'].notnull(), 'int'].astype(np.int32)

        df2 = pd.read_csv(os.path.join(self.basic_data_folder, "df2.csv"), dtype=df2_dtypes)

        df3 = pd.read_csv(os.path.join(self.basic_data_folder, "df3.csv"), parse_dates=[0, 1])

        self.df1 = df1
        self.df1_tstamp = df1_tstamp
        self.df2 = df2
        self.df3 = df3

        df1_rownames = df1.copy()
        df1_rownames['rownames'] = ['A', 'B', 'C',"D",'E','F']
        df1_rownames = df1_rownames.set_index('rownames')
        self.df1_rownames = df1_rownames

        self.rdata_objects = ['df1', 'df2', 'char']
        self.rdata_objects_description = [{"object_name": "df1", "columns": ['num', 'int', 'char', 'fac', 'log', 'tstamp1', 'tstamp2']},
            {"object_name": "df2", "columns": ['num2', 'int2', 'char2', 'fac2', 'log2']},
            {"object_name": "char", "columns": []}]
        self.use_objects = ["df1"]
        
        t = datetime.datetime(1960, 1, 1)
        sec = [np.nan] * 8
        sec[7] = 2
        third = [np.nan] * 8
        third[7] = 3
        third[0] = ""
        colnames = ["char", "int", "num", "log", "datetime", "date", "object", "categ"]
        df_out = pd.DataFrame([["a", 1, 2.2, True, t, t.date(), t.time(), 1], sec, third], columns=colnames)
        df_out["int"] = df_out["int"].astype("object")
        df_out.iloc[0, 1] = np.int32(df_out.iloc[0, 1])
        df_out["categ"] = df_out["categ"].astype("category")
        self.df_out = df_out
        
        self.df_international_win = pd.read_csv(os.path.join(self.basic_data_folder, "international_win.csv"))

        df_dates = pd.read_csv(os.path.join(self.basic_data_folder, "dates.csv"))
        df_dates["d"] = df_dates["d"].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date() if type(x) == str else None)
        self.df_dates = df_dates

        # matrices
        matdata = np.asarray(list(range(1,13)), dtype=np.int32)
        self.mat_singlecol = pd.DataFrame(matdata)
        self.mat_singlecol_named = pd.DataFrame(matdata, index=list(ascii_uppercase)[0:12])
        self.mat_simple = pd.DataFrame(np.reshape(matdata, (4,3), order='F'))
        self.mat_simple_byrow = pd.DataFrame(np.reshape(matdata, (4,3), order='C'))
        self.mat_rowcolnames = pd.DataFrame(np.reshape(matdata, (4,3), order='F'), 
                          columns=['V'+str(x) for x in range(1,4)],
                          index=["A", "B","C","D"])
        self.mat_rownames = pd.DataFrame(np.reshape(matdata, (4,3), order='F'), 
                          index=["A", "B","C","D"])
        self.mat_colnames = pd.DataFrame(np.reshape(matdata, (4,3), order='F'), 
                          columns=['V'+str(x) for x in range(1,4)])
        self.table = pd.DataFrame(np.asarray([[2,2], [2,2]], dtype=np.int32), 
                                columns=["0", "1"],
                                index=["0","1"])
        flat3d = np.asarray(list(range(1,37)), dtype=np.int32)
        self.array3d = xr.DataArray(np.reshape(flat3d, (4,3,3), order='F'))
        self.array3d_named = xr.DataArray(np.reshape(flat3d, (4,3,3), order='F'),
                                          [["A", "B","C","D"],
                                           ['V'+str(x) for x in range(1,4)],
                                           ['D'+str(x) for x in range(1,4)]])
        matnan = np.asarray(matdata, dtype=object)
        matnan[2:4] = np.nan
        self.mat_nan = pd.DataFrame(np.reshape(matnan, (4,3), order='F'))
        matnan_num = np.asarray(matdata, dtype=np.float64) * 100000
        self.mat_numeric = pd.DataFrame(np.reshape(matnan_num, (4,3), order='F'))
        matnan_bool = np.asarray(matnan, dtype=bool)
        matnan_bool = np.asarray(matnan_bool, dtype=object)
        matnan_bool[2:4] = np.nan
        self.mat_bool = pd.DataFrame(np.reshape(matnan_bool, (4,3), order='F'))
        matzeros = np.zeros(12)
        matzeros[2:4] = np.nan
        matdtime = pd.to_datetime(matzeros)
        matdtime = np.reshape(matdtime.values, (4,3), order='F')
        self.mat_dtime = pd.DataFrame(matdtime)
        matdate = matzeros.astype("datetime64[D]").astype(datetime.datetime)
        matdate = np.reshape(matdate, (4,3), order='F')
        self.mat_date = pd.DataFrame(matdate)
        # string
        matstr = np.asarray(["james", "cecil","zoe", "amber", np.nan, "rob"]*2, dtype=object)
        self.mat_str = pd.DataFrame(np.reshape(matstr, (4,3), order='F'))
        # categories
        mat_cat = self.mat_str.copy()
        self.mat_cat = mat_cat.astype("category")

    def test_rdata_basic(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy comparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(self.df1.equals(res['df1']))
        self.assertTrue(self.df2.equals(res['df2']))
    
    def test_rdata_pathlib(self):
        if is_pathlib_available:
            rdata_path = Path(self.basic_data_folder).joinpath("two.RData")
            res = pyreadr.read_r(rdata_path)
            self.assertListEqual(list(res.keys()), self.rdata_objects)
            # numpy comparing nans raises a runtimewarning, let's ignore that here
            warnings.simplefilter("ignore", category=RuntimeWarning)
            self.assertTrue(self.df1.equals(res['df1']))
            self.assertTrue(self.df2.equals(res['df2']))
        
    def test_rdata_rownames(self):

        rdata_path = os.path.join(self.basic_data_folder, "two_rownames.RData")
        res = pyreadr.read_r(rdata_path)
        # numpy comparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(self.df1_rownames.equals(res['df1_rownames']))
        
    def test_rdata_basic_r36(self):
        """
        same test but data saved with R 3.6.1
        """

        rdata_path = os.path.join(self.basic_data_folder, "two_r36.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy comparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(self.df1.equals(res['df1']))
        self.assertTrue(self.df2.equals(res['df2']))

    def test_rds_basic(self):

        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        res = pyreadr.read_r(rds_path)
        self.assertTrue(self.df1.equals(res[None]))

    def test_rds_rownames(self):

        rds_path = os.path.join(self.basic_data_folder, "one_rownames.Rds")
        res = pyreadr.read_r(rds_path)
        self.assertTrue(self.df1_rownames.equals(res[None]))
        
    def test_rds_basic_r36(self):
        """
        same test but data saved with R 3.6.1
        """

        rds_path = os.path.join(self.basic_data_folder, "one_r36.Rds")
        res = pyreadr.read_r(rds_path)
        self.assertTrue(self.df1.equals(res[None]))

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

    def test_write_rdata_pathlib(self):
        if is_pathlib_available:    
            path = Path(self.write_data_folder).joinpath('test_pathlib.RData')
            if os.path.isfile(path):
                os.remove(path)
            pyreadr.write_rdata(path, self.df_out)
            self.assertTrue(os.path.isfile(path))
        
    def test_write_rds(self):
        
        path = os.path.join(self.write_data_folder, "test.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out)
        self.assertTrue(os.path.isfile(path))
        
    def test_rdata_international_win(self):

        rdata_path = os.path.join(self.basic_data_folder, "international.Rdata")
        res = pyreadr.read_r(rdata_path)
        df = res['df']
        df.a = df.a.astype('object')
        self.assertTrue(self.df_international_win.equals(df))
        
    def test_rds_international_win(self):

        rds_path = os.path.join(self.basic_data_folder, "international.rds")
        res = pyreadr.read_r(rds_path)
        df = res[None]
        df.a = df.a.astype('object')
        self.assertTrue(self.df_international_win.equals(df))

    def test_rdata_dates(self):

        rdata_path = os.path.join(self.basic_data_folder, "dates.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertTrue(self.df_dates.equals(res['df']))

    def test_rds_dates(self):

        rdata_path = os.path.join(self.basic_data_folder, "dates.rds")
        res = pyreadr.read_r(rdata_path)
        self.assertTrue(self.df_dates.equals(res[None]))
        
    def test_rds_expanduser(self):

        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        dst_path = "~/one.Rds"
        shutil.copyfile(rds_path, os.path.expanduser(dst_path) )
        res = pyreadr.read_r(dst_path)
        os.remove(os.path.expanduser(dst_path))
        self.assertTrue(self.df1.equals(res[None]))

    def test_list_objects_rdata_expanduser(self):

        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        dst_path = "~/two.RData"
        shutil.copyfile(rdata_path, os.path.expanduser(dst_path) )
        res = pyreadr.list_objects(dst_path)
        os.remove(os.path.expanduser(dst_path))
        self.assertListEqual(self.rdata_objects_description, res)

    def test_write_rds_expanduser(self):
        
        path = "~/test_expand.Rds"
        pyreadr.write_rds(path, self.df_out)
        isfile = os.path.isfile(os.path.expanduser(path))
        try:
            os.remove(os.path.expanduser(path))
        except:
            pass
        self.assertTrue(isfile)

    def test_write_rdata_expanduser(self):
        
        path = "~/Test_expand.RData"
        pyreadr.write_rdata(path, self.df_out)
        isfile = os.path.isfile(os.path.expanduser(path))
        try:
            os.remove(os.path.expanduser(path))
        except:
            pass
        self.assertTrue(isfile)

    def test_rdata_bzip2(self):

        rdata_path = os.path.join(self.basic_data_folder, "two_bzip2.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy comparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        # for some reason when R saves with bzip2 compression dates go to character -> probably it's coming from my R script
        self.assertTrue(self.df1_tstamp.equals(res['df1']))
        self.assertTrue(self.df2.equals(res['df2']))

    def test_rdata_lzma(self):

        rdata_path = os.path.join(self.basic_data_folder, "two_xz.RData")
        res = pyreadr.read_r(rdata_path)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy comparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        df1 = res['df1']
        df2 = res['df2']
        self.assertTrue(self.df1_tstamp.equals(df1))
        self.assertTrue(self.df2.equals(df2))

    def test_write_rdata_gzip(self):
        
        path = os.path.join(self.write_data_folder, "test_gzip.RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, self.df_out, compress="gzip")
        self.assertTrue(os.path.isfile(path))

    def test_write_rds_gzip(self):
        
        path = os.path.join(self.write_data_folder, "test_gzip.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out, compress="gzip")
        self.assertTrue(os.path.isfile(path))

    def test_altrep_deferred_string(self):
        path = os.path.join(self.basic_data_folder, "altrep_defstr.rds")
        res = pyreadr.read_r(path)
        self.assertEqual(res[None].iloc[0,0], '14901')

    def test_altrep_compact_intseq(self):
        path = os.path.join(self.basic_data_folder, "altrep_intseq.rdata")
        res = pyreadr.read_r(path)
        self.assertEqual(res['df']['vec'].iloc[0], 1)
        self.assertEqual(res['df']['vec'].iloc[9], 10)

    def test_altrep_wrap_real(self):
        path = os.path.join(self.basic_data_folder, "altrep_wrapreal.rdata")
        res = pyreadr.read_r(path)
        self.assertEqual(res['stderror']['logbeta'][0], 0.1508568509311767)
        self.assertEqual(res['stderror']['logmu'][0], 0.9572626097649835)

    def test_read_from_url(self):
        path = os.path.join(self.write_data_folder, "airlines.rda")
        url = "https://github.com/hadley/nycflights13/blob/main/data/airlines.rda?raw=true"
        res = pyreadr.read_r(pyreadr.download_file(url, path))
        self.assertIsNotNone(res)

    # matrices
    def test_matrix_simple_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_simple.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_simple))

    def test_matrix_simple_byrow_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_simple_byrow.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_simple_byrow))

    def test_matrix_rowcolnames(self):
        path = os.path.join(self.basic_data_folder, "mat_rowcolnames.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_rowcolnames))

    def test_matrix_colnames(self):
        path = os.path.join(self.basic_data_folder, "mat_colnames.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_colnames))

    def test_matrix_rownames(self):
        path = os.path.join(self.basic_data_folder, "mat_rownames.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_rownames))

    def test_table(self):
        path = os.path.join(self.basic_data_folder, "table.rds")
        res = pyreadr.read_r(path)
        df = res[None] 
        #import pdb;pdb.set_trace()
        self.assertTrue(df.equals(self.table))

    def test_array_simple_rds(self):
        path = os.path.join(self.basic_data_folder, "array_simple.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_simple))

    def test_array_onedim_rds(self):
        path = os.path.join(self.basic_data_folder, "array_onedim.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_singlecol))

    def test_array_onedim_named_rds(self):
        path = os.path.join(self.basic_data_folder, "array_onedim_named.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_singlecol_named))

    def test_array_3d(self):
        path = os.path.join(self.basic_data_folder, "array_3d.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.array3d))

    def test_array_3dnamed(self):
        path = os.path.join(self.basic_data_folder, "array_3d_named.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.array3d_named))

    def test_matrix_integernans_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_na.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_nan))

    def test_matrix_numeric_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_numeric.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_numeric))

    def test_matrix_logic_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_bool.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_bool))

    def test_matrix_dtime_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_dtime.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(df.equals(self.mat_dtime))

    def test_matrix_date_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_date.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertTrue(df.equals(self.mat_date))

    def test_matrix_string_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_str.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_str))

    def test_matrix_category_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_factor.rds")
        res = pyreadr.read_r(path)
        df = res[None]
        self.assertTrue(df.equals(self.mat_cat))

 
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
