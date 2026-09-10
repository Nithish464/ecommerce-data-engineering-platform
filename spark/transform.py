from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum, count
spark=SparkSession.builder.appName('EcommerceTransform').getOrCreate()
orders=spark.read.option('header',True).csv('/opt/spark-apps/../data/orders.csv',inferSchema=True)
items=spark.read.option('header',True).csv('/opt/spark-apps/../data/order_items.csv',inferSchema=True)
products=spark.read.option('header',True).csv('/opt/spark-apps/../data/products.csv',inferSchema=True)
summary=items.join(products,'product_id').groupBy('product_id','name').agg(_sum('quantity').alias('units'),_sum(col('quantity')*col('unit_price')).alias('revenue')).orderBy(col('revenue').desc())
summary.show()
spark.stop()
