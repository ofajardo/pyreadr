"""
Narwhalified tests for pyreadr - runs with both pandas and polars backends.
Usage: python tests/test_narwhalified.py --inplace --backend=pandas
       python tests/test_narwhalified.py --inplace --backend=polars

@author: Otto Fajardo
"""
import unittest
import io
import os
import datetime
import math
import warnings
import shutil
import urllib
from collections import OrderedDict
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

pandas_version = tuple(int(x) for x in pd.__version__.split(".")[:2])
is_pandas_3 = pandas_version[0] > 2
# pd.to_datetime(..., unit='s') on whole seconds infers datetime64[s] in pandas 3.0
# and datetime64[us] from pandas 3.1 on
pandas3_dt_unit = 'datetime64[s]' if pandas_version < (3, 1) else 'datetime64[us]'

# R factor levels (in R order) of the factor columns in the test files; polars reads factors as Enum
fac_levels = ['amber', 'cecil', 'james', 'rob', 'zoe']
fac2_levels = ['d', 'e', 'f']


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
                df1['tstamp1'] = df1['tstamp1'].astype(pandas3_dt_unit)
                df1['tstamp2'] = df1['tstamp2'].astype(pandas3_dt_unit)
            df1 = nw.from_native(df1)
        else:
            df1_native = df1.to_native()
            df1_native = df1_native.with_columns(
                pl.when(pl.col('num') == 'Inf').then(float('inf'))
                  .otherwise(pl.col('num').cast(pl.Float64, strict=False))
                  .alias('num')
            )
            # R's df1$num is c(1, 2, 3, Inf, NA, NaN): write.csv writes NaN as NA, polars keeps NaN apart from null
            df1_native = df1_native.with_columns(
                pl.when(pl.int_range(pl.len()) == 5).then(float('nan')).otherwise(pl.col('num')).alias('num')
            )
            df1 = nw.from_native(df1_native)
            df1 = df1.with_columns(nw.col('int').cast(nw.Int32), nw.col('fac').cast(nw.Enum(fac_levels)))

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
            # NaN in the last row, see df1
            df1t_native = df1t_native.with_columns(
                pl.when(pl.int_range(pl.len()) == 5).then(float('nan')).otherwise(pl.col('num')).alias('num')
            )
            df1_tstamp = nw.from_native(df1t_native)
            df1_tstamp = df1_tstamp.with_columns(nw.col('int').cast(nw.Int32), nw.col('fac').cast(nw.Enum(fac_levels)))

        self.df1_tstamp = df1_tstamp.to_native()

        # --- df2 ---
        df2 = nw.read_csv(os.path.join(self.basic_data_folder, "df2.csv"), backend=self.backend)
        df2 = df2.with_columns(
            nw.col("int2").cast(nw.Int32),
            nw.col("num2").cast(nw.Float64),
            nw.col("fac2").cast(nw.Enum(fac2_levels) if self.backend == "polars" else nw.Categorical),
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
                df3['tstampa'] = df3['tstampa'].astype(pandas3_dt_unit)
                df3['tstampb'] = df3['tstampb'].astype(pandas3_dt_unit)
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
            # a factor matrix has one set of levels for all columns
            self.mat_cat = self.mat_str.apply(lambda c: pd.Categorical(c, categories=fac_levels))
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
                '0': pl.Series('0', ['james', 'cecil', 'zoe', 'amber'], dtype=pl.Enum(fac_levels)),
                '1': pl.Series('1', [None, 'rob', 'james', 'cecil'], dtype=pl.Enum(fac_levels)),
                '2': pl.Series('2', ['zoe', 'amber', None, 'rob'], dtype=pl.Enum(fac_levels)),
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

    def test_list_objects_path_types(self):
        # same path types as read_r: str, bytes, Path and file-like objects
        rdata_path = os.path.join(self.basic_data_folder, "two.RData")
        with open(rdata_path, "rb") as fh:
            content = fh.read()
        for path in (rdata_path, os.fsencode(rdata_path), Path(rdata_path), io.BytesIO(content)):
            self.assertListEqual(self.rdata_objects_description, pyreadr.list_objects(path), repr(path))
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.list_objects(os.path.join(self.basic_data_folder, "nope.RData"))

    def test_list_objects_rownames(self):
        rdata_path = os.path.join(self.basic_data_folder, "two_rownames.RData")
        res = pyreadr.list_objects(rdata_path)
        expected = [dict(self.rdata_objects_description[0], object_name="df1_rownames")] + self.rdata_objects_description[1:]
        self.assertListEqual(expected, res)

        rds_path = os.path.join(self.basic_data_folder, "one_rownames.Rds")
        res = pyreadr.list_objects(rds_path)
        expected = [dict(self.rdata_objects_description[0], object_name=None)]
        self.assertListEqual(expected, res)

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
    # Read tests — encoding (file declares UTF-8 but has unflagged latin1 strings, issue #49)
    # ==========================================================================

    def test_rdata_encoding_latin1(self):
        path = os.path.join(self.basic_data_folder, "latin1_unflagged.RData")
        res = pyreadr.read_r(path, encoding="latin1", output_format=self.backend)
        lv = "(±)-(E)-2-Octen-4-ol"
        if self.backend == "polars":
            expected = pl.DataFrame({
                'name': pl.Series('name', [lv, 'plain', lv], dtype=pl.Enum([lv, 'plain'])),
                'série': ['café', 'abc', None],
            })
        else:
            expected = pd.DataFrame({'name': [lv, 'plain', lv], 'série': ['café', 'abc', np.nan]})
            expected['name'] = expected['name'].astype('category')
        self.assertFrameEqual(res['df_latin1'], expected)

    def test_rdata_encoding_default_fails(self):
        path = os.path.join(self.basic_data_folder, "latin1_unflagged.RData")
        with self.assertRaises(UnicodeDecodeError):
            pyreadr.read_r(path, output_format=self.backend)

    def test_list_objects_encoding(self):
        path = os.path.join(self.basic_data_folder, "latin1_unflagged.RData")
        res = pyreadr.list_objects(path, encoding="latin1")
        self.assertListEqual([{"object_name": "df_latin1", "columns": ["name", "série"]}], res)

    def test_invalid_encoding(self):
        path = os.path.join(self.basic_data_folder, "latin1_unflagged.RData")
        with self.assertRaises(pyreadr.LibrdataError):
            pyreadr.read_r(path, encoding="not-a-charset", output_format=self.backend)

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

    def test_factor_unused_levels(self):
        # levels c, b, a: not alphabetical and c is unused; both must be kept as in R
        path = os.path.join(self.basic_data_folder, "factor_unused_levels.RData")
        res = pyreadr.read_r(path, output_format=self.backend)
        df = res['df']
        levels = ['c', 'b', 'a']
        if self.backend == "polars":
            expected = pl.DataFrame({'f': pl.Series('f', ['b', 'a', None, 'b'], dtype=pl.Enum(levels))})
            self.assertEqual(df['f'].dtype, pl.Enum(levels))
        else:
            expected = pd.DataFrame({'f': pd.Categorical(['b', 'a', np.nan, 'b'], categories=levels)})
            # pandas equals ignores the order of categories, check it explicitly
            self.assertListEqual(df['f'].cat.categories.tolist(), levels)
            self.assertFalse(df['f'].cat.ordered)
        self.assertFrameEqual(df, expected)

    def test_factor_na_level(self):
        # addNA(): NA is a level in R (levels a, b, NA). pandas categories and polars Enum cannot have a missing
        # level, the NA level is dropped and its values become missing
        path = os.path.join(self.basic_data_folder, "factor_na_level.rds")
        df = pyreadr.read_r(path, output_format=self.backend)[None]
        levels = ['a', 'b']
        if self.backend == "polars":
            expected = pl.DataFrame({
                'f': pl.Series('f', ['a', None, 'b', 'a'], dtype=pl.Enum(levels)),
                'x': [1.0, 2.0, 3.0, 4.0],
            })
        else:
            expected = pd.DataFrame({
                'f': pd.Categorical(['a', np.nan, 'b', 'a'], categories=levels),
                'x': [1.0, 2.0, 3.0, 4.0],
            })
            self.assertListEqual(df['f'].cat.categories.tolist(), levels)
        self.assertFrameEqual(df, expected)

    def test_read_na_nan(self):
        # R: x = c(1.5, NA, NaN, 4), d = as.Date(c("2020-01-01", NA, "2020-01-03", NA))
        path = os.path.join(self.basic_data_folder, "na_nan.rds")
        df = pyreadr.read_r(path, output_format=self.backend)[None]
        if self.backend == "polars":
            # NA is null, NaN stays NaN
            x = df['x'].to_list()
            self.assertEqual(x[0], 1.5)
            self.assertIsNone(x[1])
            self.assertTrue(math.isnan(x[2]))
            self.assertEqual(x[3], 4.0)
            self.assertListEqual(df['x'].is_null().to_list(), [False, True, False, False])
            self.assertListEqual(df['x'].is_nan().to_list(), [False, None, True, False])
            self.assertListEqual(df['d'].to_list(),
                                 [datetime.date(2020, 1, 1), None, datetime.date(2020, 1, 3), None])
        else:
            # pandas has only NaN for both
            x = df['x'].tolist()
            self.assertEqual(x[0], 1.5)
            self.assertTrue(math.isnan(x[1]))
            self.assertTrue(math.isnan(x[2]))
            self.assertEqual(x[3], 4.0)
            self.assertListEqual(df['d'].isna().tolist(), [False, True, False, True])

    # ==========================================================================
    # Read tests — row_offset and row_limit
    # ==========================================================================

    def _rows(self, expected, offset, limit):
        """expected rows offset to offset + limit (limit 0: all), default pandas index restarting at 0"""
        if self.backend == "polars":
            return expected.slice(offset, limit if limit else None)
        res = expected.iloc[offset:offset + limit] if limit else expected.iloc[offset:]
        if isinstance(expected.index, pd.RangeIndex):
            res = res.reset_index(drop=True)
        return res

    def test_read_rows_dataframe(self):
        # rows 3 to 5 keep the missing values of every column, so pandas dtypes are the same as in the full frame
        path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(path, output_format=self.backend, row_offset=3, row_limit=3)
        self.assertFrameEqual(res['df1'], self._rows(self.df1, 3, 3))
        self.assertFrameEqual(res['df2'], self._rows(self.df2, 3, 3))
        # factors keep all levels
        if self.backend == "polars":
            self.assertEqual(res['df1']['fac'].dtype, pl.Enum(fac_levels))
        else:
            self.assertListEqual(res['df1']['fac'].cat.categories.tolist(), fac_levels)

    def test_read_rows_offset_only(self):
        path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(path, output_format=self.backend, row_offset=4, use_objects=['df1'])
        self.assertFrameEqual(res['df1'], self._rows(self.df1, 4, 0))

    def test_read_rows_rownames(self):
        path = os.path.join(self.basic_data_folder, "two_rownames.RData")
        res = pyreadr.read_r(path, output_format=self.backend, row_offset=3, row_limit=3)
        self.assertFrameEqual(res['df1_rownames'], self._rows(self.df1_rownames, 3, 3))

    def test_read_rows_matrix(self):
        # matrices are stored by column in R: rows are selected after building the matrix
        for f, expected in (("mat_simple.rds", self.mat_simple), ("mat_rownames.rds", self.mat_rownames),
                            ("mat_str.rds", self.mat_str), ("mat_factor.rds", self.mat_cat)):
            res = pyreadr.read_r(os.path.join(self.basic_data_folder, f), output_format=self.backend,
                                 row_offset=1, row_limit=2)
            self.assertFrameEqual(res[None], self._rows(expected, 1, 2))

    def test_read_rows_beyond_end(self):
        path = os.path.join(self.basic_data_folder, "two.RData")
        res = pyreadr.read_r(path, output_format=self.backend, row_offset=10, use_objects=['df1'])
        self.assertEqual(res['df1'].shape, (0, self.df1.shape[1]))
        self.assertListEqual(list(res['df1'].columns), list(self.df1.columns))

    def test_read_rows_invalid(self):
        path = os.path.join(self.basic_data_folder, "two.RData")
        for kwargs in ({"row_offset": -1}, {"row_limit": -1}, {"row_offset": 1.5}, {"row_limit": "3"}):
            with self.assertRaises(pyreadr.PyreadrError, msg=repr(kwargs)):
                pyreadr.read_r(path, output_format=self.backend, **kwargs)

    # ==========================================================================
    # read_metadata
    # ==========================================================================

    def test_read_metadata(self):
        # files written by R 4.3.3 with different formats and compressions
        cases = {
            "meta_v3_xz.RData": {"file_type": "RData", "format_version": 3, "compression": "xz",
                                 "writer_r_version": "4.3.3", "min_reader_r_version": "3.5.0"},
            "meta_v3_gzip.RData": {"file_type": "RData", "format_version": 3, "compression": "gzip",
                                   "writer_r_version": "4.3.3", "min_reader_r_version": "3.5.0"},
            "meta_v2_bzip2.rds": {"file_type": "Rds", "format_version": 2, "compression": "bzip2",
                                  "writer_r_version": "4.3.3", "min_reader_r_version": "2.3.0"},
            "meta_v3_none.rds": {"file_type": "Rds", "format_version": 3, "compression": None,
                                 "writer_r_version": "4.3.3", "min_reader_r_version": "3.5.0"},
        }
        for f, expected in cases.items():
            self.assertDictEqual(pyreadr.read_metadata(os.path.join(self.basic_data_folder, f)), expected, f)

    def test_read_metadata_file_object(self):
        with open(os.path.join(self.basic_data_folder, "meta_v3_xz.RData"), "rb") as fh:
            meta = pyreadr.read_metadata(io.BytesIO(fh.read()))
        self.assertEqual(meta["file_type"], "RData")
        self.assertEqual(meta["compression"], "xz")

    def test_read_metadata_written_by_pyreadr(self):
        path = os.path.join(self.write_data_folder, "test_nw_metadata.RData")
        pyreadr.write_rdata(path, self.df_out, compress="gzip")
        self.assertDictEqual(pyreadr.read_metadata(path),
                             {"file_type": "RData", "format_version": 2, "compression": "gzip",
                              "writer_r_version": "2.3.0", "min_reader_r_version": "2.3.0"})

    def test_read_metadata_not_found(self):
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.read_metadata(os.path.join(self.basic_data_folder, "nope.RData"))

    def test_read_error_details(self):
        # a list whose element has the unknown S-expression type 30 (as from a newer R version, or a damaged
        # file): librdata's detailed message is part of the error
        path = os.path.join(self.basic_data_folder, "unknown_sexp.rds")
        with self.assertRaisesRegex(pyreadr.LibrdataError,
                                    "^The file contains an unrecognized object: Unhandled S-Expression: 30$"):
            pyreadr.read_r(path, output_format=self.backend)

    def test_read_dates_na_no_warning(self):
        # missing dates (data frame and matrix) must not raise a RuntimeWarning when converted
        for f in ("dates.RData", "dates.rds", "mat_date.rds", "na_nan.rds"):
            with warnings.catch_warnings():
                warnings.simplefilter("error", category=RuntimeWarning)
                pyreadr.read_r(os.path.join(self.basic_data_folder, f), output_format=self.backend)

    def test_read_s4_skipped(self):
        # librdata skips S4 objects, the other objects in the workspace are read
        path = os.path.join(self.basic_data_folder, "s4_and_df.RData")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            res = pyreadr.read_r(path, output_format=self.backend)
        self.assertListEqual(list(res.keys()), ['df'])
        self.assertListEqual(list(res['df']['x']), [1, 2, 3])

    def test_read_nothing_readable_warns(self):
        # a file with only a list: nothing can be read, read_r warns and returns an empty dict
        path = os.path.join(self.basic_data_folder, "list.rds")
        with self.assertWarnsRegex(UserWarning, "no readable objects"):
            res = pyreadr.read_r(path, output_format=self.backend)
        self.assertEqual(len(res), 0)

    def test_na_colname(self):
        # names(df)[1] <- NA in R: the column name is missing
        path = os.path.join(self.basic_data_folder, "na_colname.rds")
        df = pyreadr.read_r(path, output_format=self.backend)[None]
        if self.backend == "polars":
            expected = pl.DataFrame({
                '': pl.Series('', [1, 2], dtype=pl.Int32),
                'b': pl.Series('b', [3, 4], dtype=pl.Int32),
            })
        else:
            expected = pd.DataFrame({None: np.array([1, 2], dtype=np.int32), 'b': np.array([3, 4], dtype=np.int32)})
        self.assertFrameEqual(df, expected)

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
    # Write tests — row names
    # ==========================================================================

    def _rownames_df(self, ids):
        data = {'id': ids, 'x': [1.0, 2.0, 3.0], 'y': ['p', 'q', 'r']}
        if self.backend == "polars":
            return pl.DataFrame(data)
        return pd.DataFrame(data)

    def _write_read_rownames(self, df, name, **kwargs):
        """writes df as Rds and RData, reads both back and returns a list of (rownames, columns)"""
        out = []
        for ext, writer, key in ((".Rds", pyreadr.write_rds, None), (".RData", pyreadr.write_rdata, "dataset")):
            path = os.path.join(self.write_data_folder, name + ext)
            if os.path.isfile(path):
                os.remove(path)
            writer(path, df, **kwargs)
            res = pyreadr.read_r(path, output_format=self.backend)[key]
            if self.backend == "polars":
                out.append((res['rownames'].to_list(), [c for c in res.columns if c != 'rownames']))
            else:
                out.append((list(res.index), list(res.columns)))
        return out

    def test_write_rownames_index(self):
        if self.backend != "pandas":
            self.skipTest("polars has no index")
        df = self._rownames_df(['a', 'b', 'c']).set_index('id')
        for rownames, columns in self._write_read_rownames(df, "test_nw_rownames_index"):
            self.assertListEqual(rownames, ['a', 'b', 'c'])
            self.assertListEqual(columns, ['x', 'y'])

    def test_write_rownames_column(self):
        df = self._rownames_df(['a', 'b', 'c'])
        for rownames, columns in self._write_read_rownames(df, "test_nw_rownames_column", rownames_column="id"):
            self.assertListEqual(rownames, ['a', 'b', 'c'])
            self.assertListEqual(columns, ['x', 'y'])

    def test_write_default_rownames(self):
        df = self._rownames_df(['a', 'b', 'c'])
        for rownames, columns in self._write_read_rownames(df, "test_nw_rownames_default"):
            self.assertListEqual(rownames, ['1', '2', '3'])
            self.assertListEqual(columns, ['id', 'x', 'y'])

    def test_write_rownames_duplicates(self):
        df = self._rownames_df(['a', 'a', 'c'])
        path = os.path.join(self.write_data_folder, "test_nw_rownames_dup.Rds")
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, df, rownames_column="id")

    def test_write_rownames_missing(self):
        df = self._rownames_df(['a', None, 'c'])
        path = os.path.join(self.write_data_folder, "test_nw_rownames_missing.Rds")
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, df, rownames_column="id")

    def test_write_rownames_column_not_found(self):
        df = self._rownames_df(['a', 'b', 'c'])
        path = os.path.join(self.write_data_folder, "test_nw_rownames_notfound.Rds")
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, df, rownames_column="nope")

    def test_write_zero_rows(self):
        if self.backend == "polars":
            df = pl.DataFrame({'a': pl.Series('a', [], dtype=pl.Float64), 'b': pl.Series('b', [], dtype=pl.String)})
        else:
            df = pd.DataFrame({'a': pd.Series([], dtype=float), 'b': pd.Series([], dtype=str)})
        for ext, writer, key in ((".Rds", pyreadr.write_rds, None), (".RData", pyreadr.write_rdata, "dataset")):
            path = os.path.join(self.write_data_folder, "test_nw_zero_rows" + ext)
            if os.path.isfile(path):
                os.remove(path)
            writer(path, df)
            res = nw.from_native(pyreadr.read_r(path, output_format=self.backend)[key])
            self.assertListEqual(res.columns, ['a', 'b'])
            self.assertEqual(res.shape[0], 0)
            # empty columns keep the type of the R vector
            self.assertEqual(res.schema['a'], nw.Float64)
            self.assertEqual(res.schema['b'], nw.String)

    def test_write_zero_columns(self):
        # polars cannot have rows without columns
        if self.backend == "polars":
            df, nrows = pl.DataFrame(), 0
        else:
            df, nrows = pd.DataFrame(index=range(3)), 3
        for ext, writer, key in ((".Rds", pyreadr.write_rds, None), (".RData", pyreadr.write_rdata, "dataset")):
            path = os.path.join(self.write_data_folder, "test_nw_zero_columns" + ext)
            if os.path.isfile(path):
                os.remove(path)
            writer(path, df)
            res = pyreadr.read_r(path, output_format=self.backend)[key]
            self.assertListEqual([c for c in res.columns if c != 'rownames'], [])
            self.assertEqual(len(res), nrows)

    def test_write_compress_not_supported(self):
        path = os.path.join(self.write_data_folder, "test_nw_bz2.Rds")
        for p in (path, path + "_temp"):
            if os.path.isfile(p):
                os.remove(p)
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, self.df_out, compress="bz2")
        self.assertFalse(os.path.isfile(path + "_temp"))
        self.assertFalse(os.path.isfile(path))

    def test_write_rownames_multiindex(self):
        if self.backend != "pandas":
            self.skipTest("polars has no index")
        df = self._rownames_df(['a', 'b', 'c']).set_index(['id', 'y'])
        path = os.path.join(self.write_data_folder, "test_nw_rownames_multiindex.Rds")
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, df)

    # ==========================================================================
    # Write tests — multiple data frames in one RData file
    # ==========================================================================

    def _multiple_frames(self):
        """two data frames with different columns and number of rows, frame b has a column id for row names"""
        if self.backend == "polars":
            a = pl.DataFrame({'x': [1.5, 2.5], 'g': pl.Series('g', ['u', 'v'], dtype=pl.Enum(['v', 'u']))})
            b = pl.DataFrame({'id': ['r1', 'r2', 'r3'], 's': ['p', None, 'q']})
        else:
            a = pd.DataFrame({'x': [1.5, 2.5], 'g': pd.Categorical(['u', 'v'], categories=['v', 'u'])})
            b = pd.DataFrame({'id': ['r1', 'r2', 'r3'], 's': ['p', None, 'q']})
        return a, b

    def _rownames_values(self, df):
        """returns (row names, dict column -> values with None for missing) of a data frame read by pyreadr"""
        if self.backend == "polars":
            rownames = df['rownames'].to_list()
            values = {c: df[c].to_list() for c in df.columns if c != 'rownames'}
        else:
            rownames = list(df.index)
            values = {c: [None if pd.isna(x) else x for x in df[c].tolist()] for c in df.columns}
        return rownames, values

    def _write_read_multiple(self, frames, name, **kwargs):
        path = os.path.join(self.write_data_folder, name + ".RData")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rdata(path, frames, **kwargs)
        return pyreadr.read_r(path, output_format=self.backend)

    def test_write_rdata_multiple(self):
        a, b = self._multiple_frames()
        res = self._write_read_multiple({'a': a, 'b': b}, "test_nw_multiple")
        self.assertListEqual(list(res.keys()), ['a', 'b'])
        self.assertTupleEqual(self._rownames_values(res['a']), (['1', '2'], {'x': [1.5, 2.5], 'g': ['u', 'v']}))
        self.assertTupleEqual(self._rownames_values(res['b']),
                              (['1', '2', '3'], {'id': ['r1', 'r2', 'r3'], 's': ['p', None, 'q']}))
        # factor levels of the first frame are kept
        if self.backend == "polars":
            self.assertEqual(res['a']['g'].dtype, pl.Enum(['v', 'u']))
        else:
            self.assertListEqual(res['a']['g'].cat.categories.tolist(), ['v', 'u'])

    def test_write_rdata_multiple_ordereddict(self):
        # the output of read_r can be written back
        a, b = self._multiple_frames()
        res = self._write_read_multiple(OrderedDict([('b', b), ('a', a)]), "test_nw_multiple_od")
        self.assertListEqual(list(res.keys()), ['b', 'a'])

    def test_write_rdata_multiple_rownames_str(self):
        # a str applies to the frames that have that column, the others get default row names
        a, b = self._multiple_frames()
        res = self._write_read_multiple({'a': a, 'b': b}, "test_nw_multiple_rn_str", rownames_column='id')
        self.assertTupleEqual(self._rownames_values(res['a']), (['1', '2'], {'x': [1.5, 2.5], 'g': ['u', 'v']}))
        self.assertTupleEqual(self._rownames_values(res['b']), (['r1', 'r2', 'r3'], {'s': ['p', None, 'q']}))

    def test_write_rdata_multiple_rownames_dict(self):
        a, b = self._multiple_frames()
        res = self._write_read_multiple({'a': a, 'b': b}, "test_nw_multiple_rn_dict", rownames_column={'b': 'id'})
        self.assertTupleEqual(self._rownames_values(res['a']), (['1', '2'], {'x': [1.5, 2.5], 'g': ['u', 'v']}))
        self.assertTupleEqual(self._rownames_values(res['b']), (['r1', 'r2', 'r3'], {'s': ['p', None, 'q']}))
        # row names are validated per frame: s has a missing value
        with self.assertRaises(pyreadr.PyreadrError):
            self._write_read_multiple({'a': a, 'b': b}, "test_nw_multiple_rn_dict_err", rownames_column={'b': 's'})

    def test_write_rdata_multiple_errors(self):
        a, b = self._multiple_frames()
        path = os.path.join(self.write_data_folder, "test_nw_multiple_err.RData")
        cases = [
            ({}, {}),                                           # no data frames
            ({'': a}, {}),                                      # empty name
            ({1: a}, {}),                                       # name not a str
            ({'a': a, 'b': [1, 2]}, {}),                        # not a data frame
            ({'a': a, 'b': b}, {'rownames_column': 'nope'}),    # column in none of the frames
            ({'a': a, 'b': b}, {'rownames_column': {'c': 'id'}}),  # frame not in the dict
            (a, {'rownames_column': {'dataset': 'x'}}),         # dict rownames_column needs a dict of frames
        ]
        for frames, kwargs in cases:
            with self.assertRaises(pyreadr.PyreadrError, msg=repr((frames if isinstance(frames, dict) else 'df', kwargs))):
                pyreadr.write_rdata(path, frames, **kwargs)

    def test_write_rds_multiple_error(self):
        # a Rds file holds one object
        a, b = self._multiple_frames()
        path = os.path.join(self.write_data_folder, "test_nw_multiple_err.Rds")
        with self.assertRaises(pyreadr.PyreadrError):
            pyreadr.write_rds(path, {'a': a, 'b': b})

    # ==========================================================================
    # Write tests — NA vs NaN in numeric columns
    # ==========================================================================

    def _write_read_na_kinds(self, df, name):
        """
        writes df as Rds and RData, reads both back and returns a list of dicts column -> list of 'value', 'NA' or
        'NaN' for each row. R's NA is a NaN with 1954 in the low word; pandas output keeps the raw doubles.
        """
        out = []
        for ext, writer, key in ((".Rds", pyreadr.write_rds, None), (".RData", pyreadr.write_rdata, "dataset")):
            path = os.path.join(self.write_data_folder, name + ext)
            if os.path.isfile(path):
                os.remove(path)
            writer(path, df)
            res = pyreadr.read_r(path, output_format="pandas")[key]
            kinds = {}
            for col in res.columns:
                arr = np.asarray(res[col], dtype=np.float64)
                low = arr.view(np.uint64) & 0xFFFFFFFF
                kinds[col] = ['value' if a == a else ('NA' if lw == 1954 else 'NaN') for a, lw in zip(arr, low)]
            out.append(kinds)
        return out

    def test_write_na_nan(self):
        if self.backend == "polars":
            # null is missing (NA), NaN is NaN
            df = pl.DataFrame({
                'f': pl.Series('f', [1.0, None, float('nan')], dtype=pl.Float64),
                'i': pl.Series('i', [1, None, 3], dtype=pl.Int64),
            })
            expected = {'f': ['value', 'NA', 'NaN'], 'i': ['value', 'NA', 'value']}
        else:
            df = pd.DataFrame({
                # numpy float: NaN stays NaN
                'f': pd.Series([1.0, np.nan, None], dtype=np.float64),
                # pandas missing type pd.NA is NA
                'nf': pd.Series([1.0, None, 3.0], dtype="Float64"),
                'ni': pd.Series([1, None, 3], dtype="Int64"),
                # object: None is missing (NA), NaN is NaN
                'o': pd.Series([1.0, None, np.nan], dtype=object),
            })
            expected = {'f': ['value', 'NaN', 'NaN'], 'nf': ['value', 'NA', 'value'], 'ni': ['value', 'NA', 'value'],
                        'o': ['value', 'NA', 'NaN']}
        for kinds in self._write_read_na_kinds(df, "test_nw_na_nan"):
            self.assertDictEqual(kinds, expected)

    def test_write_na_nan_object_pd_na(self):
        if self.backend != "pandas":
            self.skipTest("pandas only")
        df = pd.DataFrame({'o': pd.Series([1.0, pd.NA, np.nan], dtype=object)})
        for kinds in self._write_read_na_kinds(df, "test_nw_na_nan_pdna"):
            self.assertDictEqual(kinds, {'o': ['value', 'NA', 'NaN']})

    def test_write_object_nan(self):
        if self.backend != "pandas":
            self.skipTest("pandas only")
        # in object columns np.nan is missing (NA) unless the other values are floats
        df = pd.DataFrame({
            'i': pd.Series([1, np.nan, 3], dtype=object),
            'b': pd.Series([True, np.nan, False], dtype=object),
            's': pd.Series(['x', np.nan, 'z'], dtype=object),
            'd': pd.Series([datetime.date(2020, 1, 2), np.nan, datetime.date(2020, 1, 3)], dtype=object),
            'm': pd.Series([1, 'a', np.nan], dtype=object),   # mixed: character
            'f': pd.Series([1.5, np.nan, 2.5], dtype=object),  # floats: NaN stays NaN
            'n': pd.Series([np.nan, np.nan, np.nan], dtype=object),
        })
        path = os.path.join(self.write_data_folder, "test_nw_object_nan.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, df)
        res = pyreadr.read_r(path)[None]
        values = {c: [None if pd.isna(x) else x for x in res[c].tolist()] for c in res.columns}
        self.assertDictEqual(values, {'i': [1, None, 3], 'b': [True, None, False], 's': ['x', None, 'z'],
                                      'd': ['2020-01-02', None, '2020-01-03'], 'm': ['1', 'a', None],
                                      'f': [1.5, None, 2.5], 'n': [None, None, None]})
        self.assertEqual(type(values['i'][0]), int)
        self.assertEqual(type(values['b'][0]), bool)
        # the R types, checked with polars output (character would be String)
        schema = pyreadr.read_r(path, output_format="polars")[None].schema
        self.assertDictEqual({c: schema[c] for c in df.columns},
                             {'i': pl.Int32, 'b': pl.Boolean, 's': pl.String, 'd': pl.String, 'm': pl.String,
                              'f': pl.Float64, 'n': pl.Float64})
        kinds = self._write_read_na_kinds(df[['f', 'n']], "test_nw_object_nan_kinds")
        for k in kinds:
            self.assertDictEqual(k, {'f': ['value', 'NaN', 'value'], 'n': ['NaN', 'NaN', 'NaN']})

    def test_write_all_missing(self):
        # untyped columns with only missing values are logical in R (as c(NA, NA)); declared string columns stay
        # character. Read back with polars: logical -> Boolean, character -> String, numeric -> Float64
        if self.backend == "polars":
            df = pl.DataFrame({
                'null': pl.Series('null', [None, None]),
                'str': pl.Series('str', [None, None], dtype=pl.String),
            })
            expected = {'null': pl.Boolean, 'str': pl.String}
        else:
            df = pd.DataFrame({
                'none': pd.Series([None, None], dtype=object),
                'nan': pd.Series([np.nan, np.nan], dtype=object),  # only NaN: numeric NaN
                'str': pd.Series([None, None], dtype="str"),
                'string': pd.Series([None, None], dtype="string"),
            })
            # in pandas 2 dtype="str" is object (untyped): logical. From pandas 3 it is a string dtype: character
            expected = {'none': pl.Boolean, 'nan': pl.Float64, 'str': pl.String if is_pandas_3 else pl.Boolean,
                        'string': pl.String}
        path = os.path.join(self.write_data_folder, "test_nw_all_missing.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, df)
        res = pyreadr.read_r(path, output_format="polars")[None]
        self.assertDictEqual({c: res.schema[c] for c in expected}, expected)
        for c in expected:
            if c == 'nan':
                self.assertListEqual(res[c].is_nan().to_list(), [True, True])
            else:
                self.assertListEqual(res[c].to_list(), [None, None])

    def test_write_duplicate_column_names(self):
        if self.backend != "pandas":
            self.skipTest("polars does not allow duplicate column names")
        df = pd.DataFrame([[1.0, 2.0]], columns=['a', 'a'])
        path = os.path.join(self.write_data_folder, "test_nw_dup_names.Rds")
        with self.assertRaisesRegex(pyreadr.PyreadrError, "duplicate column names"):
            pyreadr.write_rds(path, df)

    def test_write_pd_na(self):
        if self.backend != "pandas":
            self.skipTest("pandas only")
        # pd.NA is missing for every type
        df = pd.DataFrame({
            'nf': pd.Series([1.5, None], dtype="Float64"),
            'ni': pd.Series([1, None], dtype="Int64"),
            'ns': pd.Series(['a', None], dtype="string"),
            'os': pd.Series(['a', pd.NA], dtype=object),
            'od': pd.Series([datetime.date(2020, 1, 2), pd.NA], dtype=object),
        })
        path = os.path.join(self.write_data_folder, "test_nw_pd_na.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, df)
        res = pyreadr.read_r(path)[None]
        values = {col: [None if pd.isna(x) else x for x in res[col].tolist()] for col in res.columns}
        self.assertDictEqual(values, {'nf': [1.5, None], 'ni': [1.0, None], 'ns': ['a', None], 'os': ['a', None],
                                      'od': ['2020-01-02', None]})

    # ==========================================================================
    # Write tests — factors
    # ==========================================================================

    def _write_read_factor(self, df, name):
        """writes df as Rds and RData, reads both back and returns a list of (levels, values) of column f"""
        out = []
        for ext, writer, key in ((".Rds", pyreadr.write_rds, None), (".RData", pyreadr.write_rdata, "dataset")):
            path = os.path.join(self.write_data_folder, name + ext)
            if os.path.isfile(path):
                os.remove(path)
            writer(path, df)
            col = pyreadr.read_r(path, output_format=self.backend)[key]['f']
            if self.backend == "polars":
                self.assertIsInstance(col.dtype, pl.Enum)
                out.append((col.dtype.categories.to_list(), col.to_list()))
            else:
                self.assertEqual(col.dtype, 'category')
                out.append((col.cat.categories.tolist(), [None if x != x else x for x in col.tolist()]))
        return out

    def test_write_factor(self):
        # levels c, b, a: not alphabetical and c is unused; both must be written as in the input
        levels = ['c', 'b', 'a']
        values = ['b', 'a', None, 'b']
        if self.backend == "polars":
            df = pl.DataFrame({'f': pl.Series('f', values, dtype=pl.Enum(levels))})
        else:
            df = pd.DataFrame({'f': pd.Categorical(values, categories=levels)})
        for res_levels, res_values in self._write_read_factor(df, "test_nw_factor"):
            self.assertListEqual(res_levels, levels)
            self.assertListEqual(res_values, values)

    def test_write_factor_polars_categorical(self):
        if self.backend != "polars":
            self.skipTest("polars only")
        # polars categories are global: strings of other columns must not become levels
        pl.Series('other', ['zzz', 'yyy'], dtype=pl.Categorical)
        values = ['b', 'a', None, 'b']
        df = pl.DataFrame({'f': pl.Series('f', values, dtype=pl.Categorical)})
        for res_levels, res_values in self._write_read_factor(df, "test_nw_factor_plcat"):
            # as R's factor(): sorted unique values
            self.assertListEqual(res_levels, ['a', 'b'])
            self.assertListEqual(res_values, values)

    def test_write_factor_non_string(self):
        if self.backend != "pandas":
            self.skipTest("polars categories are always strings")
        # categories that are not strings are written with the type of the categories, not as factor
        df = pd.DataFrame({'f': pd.Categorical([3, 1, None, 3], categories=[5, 3, 1])})
        path = os.path.join(self.write_data_folder, "test_nw_factor_int.Rds")
        if os.path.isfile(path):
            os.remove(path)
        pyreadr.write_rds(path, df)
        col = pyreadr.read_r(path)[None]['f']
        self.assertEqual(col.dtype, np.float64)
        self.assertListEqual([None if x != x else x for x in col.tolist()], [3.0, 1.0, None, 3.0])

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
