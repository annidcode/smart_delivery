import pandas as pd
import numpy as np
import json
import os
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

print("Чтение фичей...")
df = pd.read_csv('/opt/airflow/data/features.csv')
print(f"Прочитано {len(df)} строк")

cat_features = ['channel', 'campaign_id']

X = df.drop(columns=['target', 'user_id'])
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train)}, Test: {len(X_test)}")
print(f"Baseline (доля read): {y.mean():.4f}")

model = CatBoostClassifier(
    iterations=500,
    learning_rate=0.05,
    depth=6,
    eval_metric='AUC',
    cat_features=cat_features,
    verbose=100,
    random_seed=42,
)

model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=50)

y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = (y_pred_proba > 0.5).astype(int)

metrics = {
    'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
    'precision': float(precision_score(y_test, y_pred, zero_division=0)),
    'recall': float(recall_score(y_test, y_pred, zero_division=0)),
    'f1': float(f1_score(y_test, y_pred, zero_division=0)),
    'train_size': int(len(X_train)),
    'test_size': int(len(X_test)),
    'baseline_read_rate': float(y.mean()),
}

print("\nМетрики:")
print(json.dumps(metrics, indent=2))

os.makedirs('/opt/airflow/data/model', exist_ok=True)
model.save_model('/opt/airflow/data/model/catboost_model.cbm')

with open('/opt/airflow/data/model/metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("\nМодель сохранена в /opt/airflow/data/model/catboost_model.cbm")
print("Метрики сохранены в /opt/airflow/data/model/metrics.json")
