import pandas as pd
import numpy as np
from datetime import datetime

NUM_ROWS = 100_000
CHANNELS = ['sms', 'notify', 'vkcm']
STATUSES = ['delivered', 'failed', 'read']
CAMPAIGNS = [f'camp_{i}' for i in range(1, 21)]

np.random.seed(42)
start_ts = int(datetime(2025, 1, 1).timestamp())
end_ts = int(datetime(2025, 3, 31).timestamp())

data = {
    'message_id': np.arange(NUM_ROWS, dtype=np.uint64),
    'user_id': np.random.randint(1_000_000, 9_999_999, NUM_ROWS).astype(np.uint64),
    'channel': np.random.choice(CHANNELS, NUM_ROWS, p=[0.6, 0.3, 0.1]),
    'campaign_id': np.random.choice(CAMPAIGNS, NUM_ROWS),
    'status': np.random.choice(STATUSES, NUM_ROWS, p=[0.7, 0.1, 0.2]),
    'cost_rub': np.round(np.random.uniform(0.5, 3.0, NUM_ROWS), 2),
    'timestamp': np.random.randint(start_ts, end_ts, NUM_ROWS),
}

df = pd.DataFrame(data)
df.loc[df['status'] == 'failed', 'cost_rub'] = 0
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

df.to_csv('/opt/airflow/data/sms_logs.csv', index=False)
print(f"Сгенерировано {len(df)} строк")
