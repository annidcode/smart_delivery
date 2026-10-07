import pandas as pd
import numpy as np
import json
import os
from catboost import CatBoostClassifier
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

print("Загрузка данных и модели...")
df = pd.read_csv('/opt/airflow/data/features.csv')
df_full = pd.read_csv('/opt/airflow/data/sms_logs.csv')

# Загружаем модель
model = CatBoostClassifier()
model.load_model('/opt/airflow/data/model/catboost_model.cbm')

cat_features = ['channel', 'campaign_id']
CHANNELS = ['sms', 'notify', 'vkcm']

# Для каждого сообщения предсказываем вероятность прочтения по каждому каналу
print("Предсказание вероятностей по каналам...")

predictions = {}
for ch in CHANNELS:
    X = df.drop(columns=['target', 'user_id']).copy()
    X['channel'] = ch  # подменяем канал
    predictions[ch] = model.predict_proba(X)[:, 1]

# Матрица вероятностей: строки — сообщения, столбцы — каналы
proba_matrix = np.column_stack([predictions[ch] for ch in CHANNELS])

# Лучший канал по модели (argmax)
best_channel_idx = np.argmax(proba_matrix, axis=1)
best_channels = np.array(CHANNELS)[best_channel_idx]

# ---- Симуляция A/B-теста ----

np.random.seed(42)

# Реальные вероятности прочтения (из наших данных)
channel_read_rates = df_full.groupby('channel')['status'].apply(
    lambda x: (x == 'read').mean()
).to_dict()

# Контроль: случайный канал
control_channels = np.random.choice(CHANNELS, size=len(df), p=[0.5, 0.3, 0.2])

# Тест: лучший канал по модели
test_channels = best_channels

# Симулируем прочтение (bernoulli с реальными вероятностями)
def simulate_read(channels, read_rates):
    probs = np.array([read_rates[ch] for ch in channels])
    return np.random.binomial(1, probs)

control_reads = simulate_read(control_channels, channel_read_rates)
test_reads = simulate_read(test_channels, channel_read_rates)

# Метрики
n_control = len(control_reads)
n_test = len(test_reads)
p_control = control_reads.mean()
p_test = test_reads.mean()
uplift_abs = p_test - p_control
uplift_rel = uplift_abs / p_control

print(f"\n=== A/B TEST RESULTS ===")
print(f"Control: n={n_control}, read_rate={p_control:.4f}")
print(f"Test:    n={n_test}, read_rate={p_test:.4f}")
print(f"Uplift absolute: {uplift_abs:+.4f} ({uplift_abs*100:+.2f} п.п.)")
print(f"Uplift relative: {uplift_rel:+.2%}")

# ---- Z-test для пропорций ----
count = np.array([test_reads.sum(), control_reads.sum()])
nobs = np.array([n_test, n_control])
z_stat, p_value = proportions_ztest(count, nobs, alternative='two-sided')

print(f"\nZ-statistic: {z_stat:.4f}")
print(f"p-value: {p_value:.6f}")

if p_value < 0.05:
    print("Результат статистически значим ✅")
else:
    print("Результат НЕ значим ❌")

# ---- Доверительные интервалы ----
def ci_proportion(successes, n, alpha=0.05):
    p = successes / n
    se = np.sqrt(p * (1 - p) / n)
    z = stats.norm.ppf(1 - alpha / 2)
    return p - z * se, p + z * se

ci_control = ci_proportion(control_reads.sum(), n_control)
ci_test = ci_proportion(test_reads.sum(), n_test)

print(f"\n95% CI Control: [{ci_control[0]:.4f}, {ci_control[1]:.4f}]")
print(f"95% CI Test:    [{ci_test[0]:.4f}, {ci_test[1]:.4f}]")

# ---- Bootstrap для разницы ----
n_bootstrap = 1000
boot_diffs = []
for _ in range(n_bootstrap):
    c = np.random.choice(control_reads, n_control, replace=True).mean()
    t = np.random.choice(test_reads, n_test, replace=True).mean()
    boot_diffs.append(t - c)

boot_diffs = np.array(boot_diffs)
ci_boot_low, ci_boot_high = np.percentile(boot_diffs, [2.5, 97.5])

print(f"\nBootstrap 95% CI diff: [{ci_boot_low:.4f}, {ci_boot_high:.4f}]")
print(f"Bootstrap mean diff: {boot_diffs.mean():.4f}")

# ---- MDE (Minimum Detectable Effect) ----
def mde(p1, n, alpha=0.05, power=0.8):
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    p2 = p1 + 0.001
    for _ in range(100):
        n_needed = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2
        if n_needed <= n:
            return p2 - p1
        p2 += 0.001
    return None

mde_value = mde(p_control, n_control)
print(f"\nMDE при n={n_control}, p1={p_control:.4f}: {mde_value*100:.2f} п.п." if mde_value else "MDE не рассчитан")

# ---- Сохраняем результат ----
results = {
    'control_n': int(n_control),
    'control_read_rate': float(p_control),
    'test_n': int(n_test),
    'test_read_rate': float(p_test),
    'uplift_absolute': float(uplift_abs),
    'uplift_relative': float(uplift_rel),
    'z_statistic': float(z_stat),
    'p_value': float(p_value),
    'significant': bool(p_value < 0.05),
    'ci_control': [float(ci_control[0]), float(ci_control[1])],
    'ci_test': [float(ci_test[0]), float(ci_test[1])],
    'bootstrap_ci_diff': [float(ci_boot_low), float(ci_boot_high)],
    'mde_pp': float(mde_value * 100) if mde_value else None,
}

os.makedirs('/opt/airflow/data/ab_test', exist_ok=True)
with open('/opt/airflow/data/ab_test/results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nРезультаты сохранены в /opt/airflow/data/ab_test/results.json")
