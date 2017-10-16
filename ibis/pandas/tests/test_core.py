import pytest

import pandas as pd
import pandas.util.testing as tm

import ibis
import ibis.expr.datatypes as dt
import ibis.expr.types as ir

pytest.importorskip('multipledispatch')

from ibis.pandas.execution import (
    execute, execute_node, execute_first
)  # noqa: E402
from ibis.pandas.client import PandasTable  # noqa: E402
from ibis.pandas.core import data_preload  # noqa: E402
from multipledispatch.conflict import ambiguities  # noqa: E402

pytestmark = pytest.mark.pandas


@pytest.fixture
def dataframe():
    return pd.DataFrame({
        'plain_int64': list(range(1, 4)),
        'plain_strings': list('abc'),
        'dup_strings': list('dad'),
    })


@pytest.fixture
def core_client(dataframe):
    return ibis.pandas.connect({'df': dataframe})


@pytest.fixture
def ibis_table(core_client):
    return core_client.table('df')


@pytest.mark.parametrize('func', [execute, execute_node, execute_first])
def test_no_execute_ambiguities(func):
    assert not ambiguities(func.funcs)


def test_execute_first_accepts_scope_keyword_argument(ibis_table, dataframe):

    param = ibis.param(dt.int64)

    @execute_first.register(ir.Node, pd.DataFrame)
    def foo(op, data, scope=None, **kwargs):
        assert scope is not None
        return data.dup_strings.str.len() + scope[param.op()]

    expr = ibis_table.dup_strings.length() + param
    assert expr.execute(params={param: 2}) is not None
    del execute_first.funcs[ir.Node, pd.DataFrame]
    execute_first.reorder()
    execute_first._cache.clear()


def test_data_preload(ibis_table, dataframe):
    @data_preload.register(PandasTable, pd.DataFrame)
    def data_preload_check_a_thing(_, df, **kwargs):
        return df

    result = ibis_table.execute()
    tm.assert_frame_equal(result, dataframe)

    del data_preload.funcs[PandasTable, pd.DataFrame]
    data_preload.reorder()
    data_preload._cache.clear()