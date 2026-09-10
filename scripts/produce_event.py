import json,os
from kafka import KafkaProducer
p=KafkaProducer(bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP','localhost:9092'),value_serializer=lambda x:json.dumps(x).encode())
p.send('order_events',{'order_id':9001,'customer_id':2,'amount':1299,'status':'created'});p.flush();print('event published')
