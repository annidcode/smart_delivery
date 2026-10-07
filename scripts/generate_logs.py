import pandas as pd
import numpy as np
from datetime import datetime, timedelta

NUM_ROWS = 100_000
CHANNELS = ['sms', 'notify', 'vkcm']
CAMPAIGNS = [f'camp_{i}' for i in range(1, 21)]

np.random.seed(42)
start_ts = datetime(2025, 1, 1).timestamp()
end_ts = datetime(2025, 3, 31).timestamp()

# Базовые вероятности прочтения по каналам
channel_read_base = {
    'sms': 0.35,      # SMS читают чаще
    'notify': 0.10,   # push легко игнорировать
    'vkcm': 0.40,     # VKCM читают хорошо
}

# Множители по времени суток (hour)
def time_multiplier(hour):
    if 7 <= hour <= 11:      # утро
        return 1.3
    elif 12 <= hour <= 17:   # день
        return 1.0
    elif 18 <= hour <= 22:   # вечер
        return 1.2
    else:                    # ночь
        return 0.3

# Генерация сообщений
messages = []
for i in range(NUM_ROWS):
    channel = np.random.choice(CHANNELS, p=[0.5, 0.3, 0.2])
    campaign = np.random.choice(CAMPAIGNS)
    cost = round(np.random.uniform(0.5, 3.0), 2)

    # Случайное время: смещение в сторону рабочих часов
    # Для реалистичности — больше сообщений днём и вечером
    hour_weights = np.array([0.3, 0.3, 0.3, 0.3, 0.3, 0.5, 0.8, 1.3, 1.5, 1.4, 1.3, 1.2,
                             1.0, 1.0, 1.0, 1.0, 1.1, 1.2, 1.3, 1.2, 1.0, 0.8, 0.5, 0.3])
    hour_weights = hour_weights / hour_weights.sum()
    hour = np.random.choice(24, p=hour_weights)

    # Timestamp
    day_offset = np.random.randint(0, 90)
    ts = datetime(2025, 1, 1) + timedelta(days=int(day_offset), hours=int(hour),
                                          minutes=int(np.random.randint(0, 60)))

    # Вероятность прочтения
    p_read = channel_read_base[channel] * time_multiplier(hour)

    # Стоимость и статус
    r = np.random.random()
    if r < p_read:
        status = 'read'
    elif r < p_read + 0.05:  # 5% — failed
        status = 'failed'
        cost = 0.0
    else:
        status = 'delivered'  # доставлено, но не прочитано

    messages.append({
        'message_id': i,
        'user_id': np.random.randint(1_000_000, 9_999_999),
        'channel': channel,
        'campaign_id': campaign,
        'status': status,
        'cost_rub': float(cost),
        'timestamp': ts,
    })

df = pd.DataFrame(messages)
df.to_csv('/opt/airflow/data/sms_logs.csv', index=False)
print(f"Сгенерировано {len(df)} строк")
print(f"\nСтатусы:\n{df['status'].value_counts()}")
print(f"\nRead rate по каналам:\n{df.groupby('channel')['status'].apply(lambda x: (x == 'read').mean())}")
