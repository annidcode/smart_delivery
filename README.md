# Smart Delivery Pipeline

End-to-end пайплайн для оптимизации каналов рассылки SMS/push/VKCM с ML, A/B-тестом и алертами.

## Бизнес-задача

Сервис отправляет сообщения по трём каналам: SMS, Notify (push), VKCM. Разные каналы имеют разную вероятность прочтения. Задача — **выбирать канал, по которому пользователь с большей вероятностью прочитает сообщение**, и проверять эффект через A/B-тест.

## Архитектура
Airflow DAG (generate_data)
↓
generate_logs — генерация 100k логов с реалистичной зависимостью read от канала и времени

load_to_clickhouse — загрузка в ClickHouse (TRUNCATE + insert для идемпотентности)

prepare_features — фичи: history, hour, day_of_week, channel, campaign

train_model — CatBoost (binary classification, ROC-AUC 0.74)

ab_test — симуляция A/B: контроль (случайный канал) vs тест (канал по модели)

alerts — проверка метрик, отправка в Telegram (fallback: файл)
↓
ClickHouse: sms_logs, features, results

## Результаты A/B-теста

| Метрика | Control | Test | Uplift |
|---|---|---|---|
| Read rate | 29.72% | 41.77% | **+12.04 п.п.** |
| Относительный uplift | — | — | **+40.5%** |
| Z-статистика | — | — | 56.19 |
| p-value | — | — | < 0.0001 |
| 95% CI diff | — | — | [11.6%, 12.4%] |

**Вывод:** модель даёт статистически значимый uplift. Доверительные интервалы не пересекаются, bootstrap CI не включает 0.

## ML-модель

- **Алгоритм:** CatBoostClassifier
- **Задача:** binary classification (`read` / `not read`)
- **Фичи:** channel, campaign_id, cost_rub, hour, day_of_week, is_weekend, user_total_msgs, user_read_rate
- **Метрики:**
  - ROC-AUC: **0.743**
  - Precision: 0.546
  - Recall: 0.181
  - F1: 0.271

## Оркестрация (Airflow)

Один DAG `generate_data` с 6 задачами:
generate_logs → load_to_clickhouse → prepare_features → train_model → ab_test → alerts


- **Идемпотентность:** `TRUNCATE TABLE` перед загрузкой → повторный запуск не задваивает данные.
- **Запуск:** вручную через Airflow UI (`schedule_interval=None`).
- **В проде:** расписание `@daily` (или OneFlow).

## Алерты

Скрипт `alerts.py` проверяет:
- Read rate в контроле < 25%
- Uplift < +5%
- A/B-тест не значим (p-value > 0.05)
- ROC-AUC модели < 0.6

**Отправка:** в Telegram. В локальной среде `api.telegram.org` заблокирован — алерт пишется в `alerts.log`. В проде — через прокси.

## Стек

- **Python:** pandas, NumPy, CatBoost, scikit-learn, SciPy, statsmodels
- **Оркестрация:** Airflow 2.9.0
- **Хранилище:** ClickHouse 24.3
- **Инфраструктура:** Docker, Docker Compose
- **Алерты:** Telegram Bot API

## Как запустить

### 1. Поднять инфраструктуру
```bash
docker compose up -d
```

Airflow UI: http://localhost:8080 (admin/admin)
ClickHouse: http://localhost:8123

2. Настроить переменные
В docker-compose.yml задать:

TELEGRAM_TOKEN

TELEGRAM_CHAT_ID

3. Запустить DAG
Airflow UI → DAG generate_data → Trigger DAG

4. Проверить результаты
```
docker exec -it airflow-scheduler cat /opt/airflow/data/ab_test/results.json
docker exec -it airflow-scheduler cat /opt/airflow/data/model/metrics.json
docker exec -it airflow-scheduler cat /opt/airflow/data/alerts.log
```
