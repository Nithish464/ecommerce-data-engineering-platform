import pandas as pd
from etl.pipeline import clean
def test_clean_removes_duplicates():
    d=pd.DataFrame({'name':[' A ',' A ']})
    assert len(clean(d))==1
def test_clean_strips_strings():
    d=pd.DataFrame({'name':[' A ']})
    assert clean(d).iloc[0,0]=='A'
