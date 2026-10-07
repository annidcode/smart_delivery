import pandas as pd
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='clickhouse', port=8123, username='admin', password='admin123'
)

client.command("""
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

# Очищаем перед заливкой
client.command("TRUNCATE TABLE sms_logs")
print("Таблица очищена")

df = pd.read_csv('/opt/airflow/data/sms_logs.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print(f"Загружаем {len(df)} строк...")

chunk_size = 50_000
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    client.insert_df('sms_logs', chunk)
    print(f"Загружено {min(i+chunk_size, len(df))}/{len(df)}")

print("Готово")
