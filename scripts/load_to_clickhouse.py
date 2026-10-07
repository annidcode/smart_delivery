import pandas as pd
from clickhouse_driver import Client

client = Client(host='clickhouse', port=9000, user='admin', password='admin123')

client.execute("""
CREATE TABLE IF NOT EXISTS sms_logs (
    message_id UInt64,
    user_id UInt64,
    channel String,
    campaign_id String,
    status String,
    cost_rub Float64,
    timestamp DateTime
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (campaign_id, channel, timestamp)
""")

df = pd.read_csv('/opt/airflow/data/sms_logs.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Загружаем {len(df)} строк...")

chunk_size = 50_000
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    client.execute('INSERT INTO sms_logs VALUES', chunk.to_dict('records'))
    print(f"Загружено {min(i+chunk_size, len(df))}/{len(df)}")

print("Готово")
