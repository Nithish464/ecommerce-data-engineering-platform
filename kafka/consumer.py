import os,json,time
from kafka import KafkaConsumer
from sqlalchemy import create_engine,text
BOOT=os.getenv('KAFKA_BOOTSTRAP','localhost:9092'); DB=os.getenv('DATABASE_URL','postgresql+psycopg2://pipeline:pipeline@localhost/ecommerce')
while True:
  try:
    c=KafkaConsumer('order_events',bootstrap_servers=BOOT,value_deserializer=lambda x:json.loads(x.decode()),auto_offset_reset='earliest',group_id='ecommerce-consumer')
    e=create_engine(DB)
    for msg in c:
      d=msg.value
      with e.begin() as conn:
        conn.execute(text("INSERT INTO pipeline_runs(pipeline,status,records) VALUES ('kafka_order_events','success',1)"))
    break
  except Exception as ex:
    print('Kafka consumer waiting:',ex); time.sleep(5)
