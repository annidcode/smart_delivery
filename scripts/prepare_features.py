import pandas as pd
import numpy as np
import clickhouse_connect
import os

CH_HOST = 'clickhouse'
client = clickhouse_connect.get_client(
    host=CH_HOST, port=8123, username='admin', password='admin123'
)

print("Чтение данных из ClickHouse...")
df = client.query_df("SELECT * FROM sms_logs")
print(f"Прочитано {len(df)} строк")

df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

df = df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
df['user_total_msgs'] = df.groupby('user_id').cumcount()
df['user_read_before'] = df.groupby('user_id')['status'].apply(
    lambda x: (x == 'read').cumsum().shift(1).fillna(0)
).reset_index(level=0, drop=True)

df['user_read_rate'] = np.where(
    df['user_total_msgs'] > 0,
    df['user_read_before'] / df['user_total_msgs'],
    0.0
)

df['target'] = (df['status'] == 'read').astype(int)

features = df[[
    'user_id', 'channel', 'campaign_id', 'cost_rub',
    'hour', 'day_of_week', 'is_weekend',
    'user_total_msgs', 'user_read_rate', 'target'
]].copy()

features.to_csv('/opt/airflow/data/features.csv', index=False)
print(f"Фичи сохранены: {len(features)} строк")
