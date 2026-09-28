"""
Narwhalified tests for pyreadr - runs with both pandas and polars backends.
Usage: python tests/test_narwhalified.py --inplace --backend=pandas
       python tests/test_narwhalified.py --inplace --backend=polars

@author: Otto Fajardo
"""
import unittest
import os
import datetime
import warnings
import shutil
import urllib
from string import ascii_uppercase

import numpy as np
import pandas as pd
import polars as pl
import xarray as xr
import narwhals.stable.v2 as nw


is_pathlib_available = False
try:
    from pathlib import Path
    is_pathlib_available = True
except:
    pass

is_pandas_3 = int(pd.__version__.split(".")[0]) > 2


class TestNarwhalified(unittest.TestCase):

    def _prepare_data(self):

        global backend
        self.backend = backend

        self.script_folder = os.path.dirname(os.path.realpath(__file__))
        self.parent_folder = os.path.split(self.script_folder)[0]
        self.data_folder = os.path.join(self.parent_folder, "test_data")
        self.basic_data_folder = os.path.join(self.data_folder, "basic")
        self.write_data_folder = os.path.join(self.data_folder, "write")

        self.rdata_objects = ['df1', 'df2', 'char']
        self.rdata_objects_description = [
            {"object_name": "df1", "columns": ['num', 'int', 'char', 'fac', 'log', 'tstamp1', 'tstamp2']},
            {"object_name": "df2", "columns": ['num2', 'int2', 'char2', 'fac2', 'log2']},
            {"object_name": "char", "columns": []}
        ]
        self.use_objects = ["df1"]

        # --- df1 ---
        csv_kwds = {}
        if self.backend == "polars":
            csv_kwds["null_values"] = "NA"
            csv_kwds["try_parse_dates"] = True
        else:
            csv_kwds["na_values"] = "NA"
            csv_kwds["keep_default_na"] = False

        df1 = nw.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), backend=self.backend, **csv_kwds)

        if self.backend == "pandas":
            df1 = df1.to_native()
            df1['int'] = df1['int'].astype(object)
            df1.loc[df1['int'].notnull(), 'int'] = df1.loc[df1['int'].notnull(), 'int'].astype(np.int32)
            df1['fac'] = df1['fac'].astype('category')
            df1['tstamp1'] = pd.to_datetime(df1['tstamp1'])
            df1['tstamp2'] = pd.to_datetime(df1['tstamp2'])
            if is_pandas_3:
                df1['tstamp1'] = df1['tstamp1'].astype('datetime64[s]')
                df1['tstamp2'] = df1['tstamp2'].astype('datetime64[s]')
            df1 = nw.from_native(df1)
        else:
            df1_native = df1.to_native()
            df1_native = df1_native.with_columns(
                pl.when(pl.col('num') == 'Inf').then(float('inf'))
                  .otherwise(pl.col('num').cast(pl.Float64, strict=False))
                  .alias('num')
            )
            df1 = nw.from_native(df1_native)
            df1 = df1.with_columns(nw.col('int').cast(nw.Int32), nw.col('fac').cast(nw.Categorical))

        self.df1 = df1.to_native()

        # --- df1_tstamp (bzip2/lzma: timestamps stay as strings) ---
        tstamp_kwds = dict(csv_kwds)
        if self.backend == "polars":
            tstamp_kwds.pop("try_parse_dates", None)
        df1_tstamp = nw.read_csv(os.path.join(self.basic_data_folder, "df1.csv"), backend=self.backend, **tstamp_kwds)

        if self.backend == "pandas":
            df1_tstamp = df1_tstamp.to_native()
            df1_tstamp['int'] = df1_tstamp['int'].astype(object)
            df1_tstamp.loc[df1_tstamp['int'].notnull(), 'int'] = df1_tstamp.loc[df1_tstamp['int'].notnull(), 'int'].astype(np.int32)
            df1_tstamp['fac'] = df1_tstamp['fac'].astype('category')
            df1_tstamp = nw.from_native(df1_tstamp)
        else:
            df1t_native = df1_tstamp.to_native()
            df1t_native = df1t_native.with_columns(
                pl.when(pl.col('num') == 'Inf').then(float('inf'))
                  .otherwise(pl.col('num').cast(pl.Float64, strict=False))
                  .alias('num')
            )
            df1_tstamp = nw.from_native(df1t_native)
            df1_tstamp = df1_tstamp.with_columns(nw.col('int').cast(nw.Int32), nw.col('fac').cast(nw.Categorical))

        self.df1_tstamp = df1_tstamp.to_native()

        # --- df2 ---
        df2 = nw.read_csv(os.path.join(self.basic_data_folder, "df2.csv"), backend=self.backend)
        df2 = df2.with_columns(
            nw.col("int2").cast(nw.Int32),
            nw.col("num2").cast(nw.Float64),
            nw.col("fac2").cast(nw.Categorical),
        )
        self.df2 = df2.to_native()

        # --- df1 with rownames ---
        if self.backend == "pandas":
            df1_rownames = self.df1.copy()
            df1_rownames['rownames'] = ['A', 'B', 'C', "D", 'E', 'F']
            df1_rownames = df1_rownames.set_index('rownames')
        else:
            df1_rownames = nw.from_native(self.df1).with_columns(
                nw.new_series('rownames', ['A', 'B', 'C', 'D', 'E', 'F'], backend=self.backend)
            ).to_native()
        self.df1_rownames = df1_rownames

        # --- df3 (tzone expected data — CET values after tz strip) ---
        df3 = nw.read_csv(os.path.join(self.basic_data_folder, "df3.csv"), backend=self.backend,
                          **({} if self.backend == "polars" else {}))
        if self.backend == "pandas":
            df3 = df3.to_native()
            df3['tstampa'] = pd.to_datetime(df3['tstampa'])
            df3['tstampb'] = pd.to_datetime(df3['tstampb'])
            if is_pandas_3:
                df3['tstampa'] = df3['tstampa'].astype('datetime64[s]')
                df3['tstampb'] = df3['tstampb'].astype('datetime64[s]')
        else:
            df3 = df3.to_native()
            df3 = df3.with_columns(
                pl.col('tstampa').str.to_datetime(),
                pl.col('tstampb').str.to_datetime(),
            )
        self.df3 = df3

        # --- international ---
        self.df_international_win = nw.read_csv(
            os.path.join(self.basic_data_folder, "international_win.csv"), backend=self.backend
        ).to_native()

        # --- dates ---
        df_dates_csv = os.path.join(self.basic_data_folder, "dates.csv")
        df_dates = nw.read_csv(df_dates_csv, backend=self.backend,
                               **({'null_values': 'NA'} if self.backend == 'polars' else
                                  {'na_values': 'NA', 'keep_default_na': False}))
        if self.backend == "pandas":
            df_dates = df_dates.to_native()
            df_dates["d"] = df_dates["d"].apply(
                lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date() if type(x) == str else None)
        else:
            df_dates = df_dates.to_native()
            df_dates = df_dates.with_columns(pl.col("d").str.to_date("%Y-%m-%d"))
        self.df_dates = df_dates

        # --- df_out for write tests ---
        t = datetime.datetime(1960, 1, 1)
        if self.backend == "pandas":
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
        else:
            df_out = pl.DataFrame({
                'char': ['a', None, ''],
                'int': pl.Series('int', [1, None, None], dtype=pl.Int32),
                'num': [2.2, None, None],
                'log': [True, None, None],
                'datetime': [t, None, None],
                'date': [t.date(), None, None],
                'categ': pl.Series('categ', ['x', None, None], dtype=pl.Categorical),
            })
        self.df_out = df_out

        # --- 3D array expected data — xr.DataArray for both backends ---
        flat3d = np.asarray(list(range(1, 37)), dtype=np.int32)
        self.array3d = xr.DataArray(np.reshape(flat3d, (4, 3, 3), order='F'))
        self.array3d_named = xr.DataArray(np.reshape(flat3d, (4, 3, 3), order='F'),
                                          [["A", "B", "C", "D"],
                                           ['V' + str(x) for x in range(1, 4)],
                                           ['D' + str(x) for x in range(1, 4)]])

        # --- 2D matrix expected data ---
        matdata = np.asarray(list(range(1, 13)), dtype=np.int32)

        if self.backend == "pandas":
            self.mat_singlecol = pd.DataFrame(matdata)
            self.mat_singlecol_named = pd.DataFrame(matdata, index=list(ascii_uppercase)[0:12])
            self.mat_simple = pd.DataFrame(np.reshape(matdata, (4, 3), order='F'))
            self.mat_simple_byrow = pd.DataFrame(np.reshape(matdata, (4, 3), order='C'))
            self.mat_rowcolnames = pd.DataFrame(np.reshape(matdata, (4, 3), order='F'),
                                                columns=['V' + str(x) for x in range(1, 4)],
                                                index=["A", "B", "C", "D"])
            self.mat_rownames = pd.DataFrame(np.reshape(matdata, (4, 3), order='F'),
                                             index=["A", "B", "C", "D"])
            self.mat_colnames = pd.DataFrame(np.reshape(matdata, (4, 3), order='F'),
                                             columns=['V' + str(x) for x in range(1, 4)])
            self.table = pd.DataFrame(np.asarray([[2, 2], [2, 2]], dtype=np.int32),
                                      columns=["0", "1"], index=["0", "1"])
            matnan = np.asarray(matdata, dtype=object)
            matnan[2:4] = np.nan
            self.mat_nan = pd.DataFrame(np.reshape(matnan, (4, 3), order='F'))
            matnan_num = np.asarray(matdata, dtype=np.float64) * 100000
            self.mat_numeric = pd.DataFrame(np.reshape(matnan_num, (4, 3), order='F'))
            matnan_bool = np.asarray(matnan, dtype=bool)
            matnan_bool = np.asarray(matnan_bool, dtype=object)
            matnan_bool[2:4] = np.nan
            self.mat_bool = pd.DataFrame(np.reshape(matnan_bool, (4, 3), order='F'))
            matzeros = np.zeros(12)
            matzeros[2:4] = np.nan
            if is_pandas_3:
                matdtime = pd.to_datetime(matzeros, unit='s')
            else:
                matdtime = pd.to_datetime(matzeros)
            matdtime = np.reshape(matdtime.values, (4, 3), order='F')
            self.mat_dtime = pd.DataFrame(matdtime)
            matdate = matzeros.astype("datetime64[D]").astype(datetime.datetime)
            matdate = np.reshape(matdate, (4, 3), order='F')
            self.mat_date = pd.DataFrame(matdate)
            matstr = np.asarray(["james", "cecil", "zoe", "amber", np.nan, "rob"] * 2, dtype=object)
            self.mat_str = pd.DataFrame(np.reshape(matstr, (4, 3), order='F'))
            mat_cat = self.mat_str.copy()
            self.mat_cat = mat_cat.astype("category")
        else:
            epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
            epoch_date = datetime.date(1970, 1, 1)
            mat_f = np.reshape(matdata, (4, 3), order='F')
            mat_c = np.reshape(matdata, (4, 3), order='C')

            self.mat_singlecol = pl.DataFrame({'0': pl.Series('0', matdata.tolist(), dtype=pl.Int32)})
            self.mat_singlecol_named = pl.DataFrame({
                '0': pl.Series('0', matdata.tolist(), dtype=pl.Int32),
                'rownames': list(ascii_uppercase)[0:12],
            })
            self.mat_simple = pl.DataFrame({str(c): pl.Series(str(c), mat_f[:, c].tolist(), dtype=pl.Int32) for c in range(3)})
            self.mat_simple_byrow = pl.DataFrame({str(c): pl.Series(str(c), mat_c[:, c].tolist(), dtype=pl.Int32) for c in range(3)})
            self.mat_rowcolnames = pl.DataFrame(
                {'V' + str(c + 1): pl.Series('V' + str(c + 1), mat_f[:, c].tolist(), dtype=pl.Int32) for c in range(3)}
            ).with_columns(pl.Series('rownames', ['A', 'B', 'C', 'D']))
            self.mat_rownames = pl.DataFrame(
                {str(c): pl.Series(str(c), mat_f[:, c].tolist(), dtype=pl.Int32) for c in range(3)}
            ).with_columns(pl.Series('rownames', ['A', 'B', 'C', 'D']))
            self.mat_colnames = pl.DataFrame(
                {'V' + str(c + 1): pl.Series('V' + str(c + 1), mat_f[:, c].tolist(), dtype=pl.Int32) for c in range(3)}
            )
            self.table = pl.DataFrame({
                '0': pl.Series('0', [2, 2], dtype=pl.Int32),
                '1': pl.Series('1', [2, 2], dtype=pl.Int32),
                'rownames': ['0', '1'],
            })
            self.mat_nan = pl.DataFrame({
                '0': pl.Series('0', [1, 2, None, None], dtype=pl.Int32),
                '1': pl.Series('1', [5, 6, 7, 8], dtype=pl.Int32),
                '2': pl.Series('2', [9, 10, 11, 12], dtype=pl.Int32),
            })
            self.mat_numeric = pl.DataFrame(
                {str(c): (mat_f[:, c].astype(np.float64) * 100000).tolist() for c in range(3)}
            )
            self.mat_bool = pl.DataFrame({
                '0': [True, True, None, None],
                '1': [True, True, True, True],
                '2': [True, True, True, True],
            })
            self.mat_dtime = pl.DataFrame({
                '0': [epoch, epoch, None, None],
                '1': [epoch, epoch, epoch, epoch],
                '2': [epoch, epoch, epoch, epoch],
            })
            self.mat_date = pl.DataFrame({
                '0': [epoch_date, epoch_date, None, None],
                '1': [epoch_date, epoch_date, epoch_date, epoch_date],
                '2': [epoch_date, epoch_date, epoch_date, epoch_date],
            })
            self.mat_str = pl.DataFrame({
                '0': ['james', 'cecil', 'zoe', 'amber'],
                '1': [None, 'rob', 'james', 'cecil'],
                '2': ['zoe', 'amber', None, 'rob'],
            })
            self.mat_cat = pl.DataFrame({
                '0': pl.Series('0', ['james', 'cecil', 'zoe', 'amber'], dtype=pl.Categorical),
                '1': pl.Series('1', [None, 'rob', 'james', 'cecil'], dtype=pl.Categorical),
                '2': pl.Series('2', ['zoe', 'amber', None, 'rob'], dtype=pl.Categorical),
            })

    def setUp(self):
        self._prepare_data()

    def assertFrameEqual(self, result, expected):
        if self.backend == "polars":
            self.assertIsInstance(result, pl.DataFrame,
                                 "Expected polars DataFrame but got %s" % type(result).__name__)
        else:
            self.assertIsInstance(result, pd.DataFrame,
                                 "Expected pandas DataFrame but got %s" % type(result).__name__)
        self.assertTrue(result.equals(expected))

    # ==========================================================================
    # Read tests — dflike path
    # ==========================================================================

    def test_rdata_basic(self):
        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        # numpy coparing nans raises a runtimewarning, let's ignore that here
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res['df1'], self.df1)
        self.assertFrameEqual(res['df2'], self.df2)

    def test_rdata_pathlib(self):
        if is_pathlib_available:
            rdata_path = Path(self.basic_data_folder).joinpath("two.RData")
            res = pyreadr.read_r(rdata_path, output_format=self.backend)
            self.assertListEqual(list(res.keys()), self.rdata_objects)
            warnings.simplefilter("ignore", category=RuntimeWarning)
            self.assertFrameEqual(res['df1'], self.df1)
            self.assertFrameEqual(res['df2'], self.df2)

    def test_rdata_rownames(self):
        rdata_path = os.path.join(self.basic_data_folder, "two_rownames.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res['df1_rownames'], self.df1_rownames)

    def test_rdata_basic_r36(self):
        rdata_path = os.path.join(self.basic_data_folder, "two_r36.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res['df1'], self.df1)
        self.assertFrameEqual(res['df2'], self.df2)

    def test_rds_basic(self):
        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        res = pyreadr.read_r(rds_path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.df1)

    def test_rds_rownames(self):
        rds_path = os.path.join(self.basic_data_folder, "one_rownames.Rds")
        res = pyreadr.read_r(rds_path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.df1_rownames)

    def test_rds_basic_r36(self):
        rds_path = os.path.join(self.basic_data_folder, "one_r36.Rds")
        res = pyreadr.read_r(rds_path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.df1)

    def test_list_objects_rdata(self):
        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.list_objects(rdata_path)
        self.assertListEqual(self.rdata_objects_description, res)

    def test_rdata_use_objects(self):
        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(rdata_path, use_objects=self.use_objects, output_format=self.backend)
        self.assertListEqual(list(res.keys()), self.use_objects)
        self.assertFrameEqual(res['df1'], self.df1)

    def test_rdata_tzone(self):
        rdata_path = os.path.join(self.basic_data_folder, "tzone.RData")
        res = pyreadr.read_r(rdata_path, timezone='CET', output_format=self.backend)
        df3 = nw.from_native(res["df3"])
        df3 = df3.with_columns(
            nw.col("tstampa").dt.replace_time_zone(None),
            nw.col("tstampb").dt.replace_time_zone(None),
        ).to_native()
        self.assertFrameEqual(df3, self.df3)

    def test_rdata_international_win(self):
        rdata_path = os.path.join(self.basic_data_folder, "international.Rdata")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        df = nw.from_native(res['df'])
        df = df.with_columns(nw.col('a').cast(nw.String)).to_native()
        self.assertFrameEqual(df, self.df_international_win)

    def test_rds_international_win(self):
        rds_path = os.path.join(self.basic_data_folder, "international.rds")
        res = pyreadr.read_r(rds_path, output_format=self.backend)
        df = nw.from_native(res[None])
        df = df.with_columns(nw.col('a').cast(nw.String)).to_native()
        self.assertFrameEqual(df, self.df_international_win)

    def test_rdata_dates(self):
        rdata_path = os.path.join(self.basic_data_folder, "dates.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertFrameEqual(res['df'], self.df_dates)

    def test_rds_dates(self):
        rdata_path = os.path.join(self.basic_data_folder, "dates.rds")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.df_dates)

    def test_rds_expanduser(self):
        rds_path = os.path.join(self.basic_data_folder, "one.Rds")
        dst_path = "~/one.Rds"
        shutil.copyfile(rds_path, os.path.expanduser(dst_path))
        res = pyreadr.read_r(dst_path, output_format=self.backend)
        os.remove(os.path.expanduser(dst_path))
        self.assertFrameEqual(res[None], self.df1)

    def test_list_objects_rdata_expanduser(self):
        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        dst_path = "~/two.RData"
        shutil.copyfile(rdata_path, os.path.expanduser(dst_path))
        res = pyreadr.list_objects(dst_path)
        os.remove(os.path.expanduser(dst_path))
        self.assertListEqual(self.rdata_objects_description, res)

    def test_rdata_bzip2(self):
        rdata_path = os.path.join(self.basic_data_folder, "two_bzip2.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res['df1'], self.df1_tstamp)
        self.assertFrameEqual(res['df2'], self.df2)

    def test_rdata_lzma(self):
        rdata_path = os.path.join(self.basic_data_folder, "two_xz.RData")
        res = pyreadr.read_r(rdata_path, output_format=self.backend)
        self.assertListEqual(list(res.keys()), self.rdata_objects)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res['df1'], self.df1_tstamp)
        self.assertFrameEqual(res['df2'], self.df2)

    def test_altrep_deferred_string(self):
        path = os.path.join(self.basic_data_folder, "altrep_defstr.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        df = res[None]
        first_col = df.columns[0]
        self.assertEqual(df[first_col].to_list()[0], '14901')

    def test_altrep_compact_intseq(self):
        path = os.path.join(self.basic_data_folder, "altrep_intseq.rdata")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertEqual(res['df']['vec'].to_list()[0], 1)
        self.assertEqual(res['df']['vec'].to_list()[9], 10)

    def test_altrep_wrap_real(self):
        path = os.path.join(self.basic_data_folder, "altrep_wrapreal.rdata")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertEqual(res['stderror']['logbeta'].to_list()[0], 0.1508568509311767)
        self.assertEqual(res['stderror']['logmu'].to_list()[0], 0.9572626097649835)

    def test_logical_vector_unnamed(self):
        path = os.path.join(self.basic_data_folder, "logical_vector.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        df = res[None]
        if self.backend == "polars":
            expected = pl.DataFrame({'': pl.Series('', [True, False, None, True])})
        else:
            expected = pd.DataFrame({None: [True, False, np.nan, True]})
        self.assertTrue(df.equals(expected))

    def test_read_from_url(self):
        path = os.path.join(self.write_data_folder, "airlines.rda")
        url = "https://github.com/hadley/nycflights13/blob/main/data/airlines.rda?raw=true"
        try:
            res = pyreadr.read_r(pyreadr.download_file(url, path), output_format=self.backend)
        except urllib.error.URLError:
            self.skipTest("Network unavailable or URL unreachable")
        self.assertIsNotNone(res)

    # ==========================================================================
    # Read tests — arraylike path (matrices, arrays, tables)
    # ==========================================================================

    def test_matrix_simple_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_simple.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_simple)

    def test_matrix_simple_byrow_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_simple_byrow.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_simple_byrow)

    def test_matrix_rowcolnames(self):
        path = os.path.join(self.basic_data_folder, "mat_rowcolnames.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_rowcolnames)

    def test_matrix_colnames(self):
        path = os.path.join(self.basic_data_folder, "mat_colnames.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_colnames)

    def test_matrix_rownames(self):
        path = os.path.join(self.basic_data_folder, "mat_rownames.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_rownames)

    def test_table(self):
        path = os.path.join(self.basic_data_folder, "table.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.table)

    def test_array_simple_rds(self):
        path = os.path.join(self.basic_data_folder, "array_simple.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_simple)

    def test_array_onedim_rds(self):
        path = os.path.join(self.basic_data_folder, "array_onedim.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_singlecol)

    def test_array_onedim_named_rds(self):
        path = os.path.join(self.basic_data_folder, "array_onedim_named.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_singlecol_named)

    def test_array_3d(self):
        path = os.path.join(self.basic_data_folder, "array_3d.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertTrue(res[None].equals(self.array3d))

    def test_array_3dnamed(self):
        path = os.path.join(self.basic_data_folder, "array_3d_named.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertTrue(res[None].equals(self.array3d_named))

    def test_matrix_integernans_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_na.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_nan)

    def test_matrix_numeric_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_numeric.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_numeric)

    def test_matrix_logic_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_bool.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_bool)

    def test_matrix_dtime_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_dtime.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        warnings.simplefilter("ignore", category=RuntimeWarning)
        self.assertFrameEqual(res[None], self.mat_dtime)

    def test_matrix_dtime_timezone_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_dtime.rds")
        res = pyreadr.read_r(path, timezone='CET', output_format=self.backend)
        df = nw.from_native(res[None])
        cols = [c for c in df.columns if c != 'rownames']
        for c in cols:
            tz = df.schema[c].time_zone
            self.assertIsNotNone(tz, "Expected timezone on column %s but got naive datetime" % c)

    def test_matrix_date_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_date.rds")
        warnings.simplefilter("ignore", category=RuntimeWarning)
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_date)

    def test_matrix_string_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_str.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_str)

    def test_matrix_category_rds(self):
        path = os.path.join(self.basic_data_folder, "mat_factor.rds")
        res = pyreadr.read_r(path, output_format=self.backend)
        self.assertFrameEqual(res[None], self.mat_cat)

    # ==========================================================================
    # Write tests
    # ==========================================================================

    def test_write_rdata(self):
        path = os.path.join(self.write_data_folder, "test_nw.RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, self.df_out)
        self.assertTrue(os.path.isfile(path))

    def test_write_rdata_pathlib(self):
        if is_pathlib_available:
            path = Path(self.write_data_folder).joinpath('test_nw_pathlib.RData')
            if os.path.isfile(path):
                os.remove(path)
            pyreadr.write_rdata(path, self.df_out)
            self.assertTrue(os.path.isfile(path))

    def test_write_rds(self):
        path = os.path.join(self.write_data_folder, "test_nw.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out)
        self.assertTrue(os.path.isfile(path))

    def test_write_rds_expanduser(self):
        path = "~/test_nw_expand.Rds"
        pyreadr.write_rds(path, self.df_out)
        isfile = os.path.isfile(os.path.expanduser(path))
        try:
            os.remove(os.path.expanduser(path))
        except:
            pass
        self.assertTrue(isfile)

    def test_write_rdata_expanduser(self):
        path = "~/Test_nw_expand.RData"
        pyreadr.write_rdata(path, self.df_out)
        isfile = os.path.isfile(os.path.expanduser(path))
        try:
            os.remove(os.path.expanduser(path))
        except:
            pass
        self.assertTrue(isfile)

    def test_write_rdata_gzip(self):
        path = os.path.join(self.write_data_folder, "test_nw_gzip.RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, self.df_out, compress="gzip")
        self.assertTrue(os.path.isfile(path))

    def test_write_rds_gzip(self):
        path = os.path.join(self.write_data_folder, "test_nw_gzip.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out, compress="gzip")
        self.assertTrue(os.path.isfile(path))

    def test_write_rdata_gzip_compresslevel(self):
        path = os.path.join(self.write_data_folder, "test_nw_gzip_cl6.RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, self.df_out, compress="gzip", compresslevel=6)
        self.assertTrue(os.path.isfile(path))
        res = pyreadr.read_r(path)
        self.assertIn('dataset', res)

    def test_write_rds_gzip_compresslevel(self):
        path = os.path.join(self.write_data_folder, "test_nw_gzip_cl6.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, self.df_out, compress="gzip", compresslevel=6)
        self.assertTrue(os.path.isfile(path))
        res = pyreadr.read_r(path)
        self.assertIn(None, res)

    # ==========================================================================
    # Error handling
    # ==========================================================================

    def test_invalid_output_format(self):
        path = os.path.join(self.basic_data_folder, "one.Rds")
        with self.assertRaises(Exception):
            pyreadr.read_r(path, output_format="invalid")


if __name__ == '__main__':

    import sys

    if "--inplace" in sys.argv:
        script_folder = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
        sys.path.insert(0, script_folder)
        sys.argv.remove('--inplace')

    backend = "pandas"
    for arg in sys.argv:
        if arg.startswith("--backend"):
            backend = arg.split("=")[1]
            sys.argv.remove(arg)
            break

    print("Using backend:", backend)

    import pyreadr

    print("package location:", pyreadr.__file__)

    unittest.main()
