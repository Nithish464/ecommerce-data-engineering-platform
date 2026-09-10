import os, pandas as pd
from sqlalchemy import create_engine, text

DB=os.getenv('DATABASE_URL','postgresql+psycopg2://pipeline:pipeline@localhost:5432/ecommerce')
BASE=os.path.join(os.path.dirname(__file__),'..','data')

def clean(df):
    df=df.drop_duplicates()
    for c in df.columns:
        if df[c].dtype == 'object': df[c]=df[c].apply(lambda x: x.strip() if isinstance(x,str) else x)
    return df

def run():
    engine=create_engine(DB)
    files=['customers','products','orders','order_items','shipments']
    started=pd.Timestamp.utcnow()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO pipeline_runs(pipeline,status,records) VALUES ('batch_etl','running',0)"))
    total=0
    try:
        for name in files:
            df=clean(pd.read_csv(os.path.join(BASE,name+'.csv')))
            if name in ('orders','order_items','shipments'):
                for c in df.columns:
                    if 'date' in c or c.endswith('_at'): df[c]=pd.to_datetime(df[c], errors='coerce')
            df.to_sql(name,engine,if_exists='append',index=False,method='multi')
            total += len(df)
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO daily_revenue SELECT order_date::date, SUM(total_amount), COUNT(*) FROM orders GROUP BY 1 ON CONFLICT(day) DO UPDATE SET revenue=EXCLUDED.revenue, orders=EXCLUDED.orders"))
            conn.execute(text("INSERT INTO top_products SELECT p.product_id,p.name,SUM(oi.quantity),SUM(oi.quantity*oi.unit_price) FROM order_items oi JOIN products p USING(product_id) GROUP BY p.product_id,p.name ON CONFLICT(product_id) DO UPDATE SET units=EXCLUDED.units,revenue=EXCLUDED.revenue"))
            conn.execute(text("UPDATE pipeline_runs SET status='success',records=:r,finished_at=now() WHERE run_id=(SELECT max(run_id) FROM pipeline_runs)"),{'r':total})
    except Exception:
        with engine.begin() as conn: conn.execute(text("UPDATE pipeline_runs SET status='failed',finished_at=now() WHERE run_id=(SELECT max(run_id) FROM pipeline_runs)"))
        raise

if __name__=='__main__': run()
