import json
import os
import requests

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

READ_RATE_THRESHOLD = 0.25  # если read rate ниже — алерт


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram не настроен, пишем в файл")
        _write_to_file(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Telegram недоступен ({e}), пишем в файл")
        _write_to_file(message)


def _write_to_file(message):
    with open('/opt/airflow/data/alerts.log', 'a') as f:
        f.write(message + "\n\n")
    print("Алерт записан в /opt/airflow/data/alerts.log")


def check_metrics():
    with open('/opt/airflow/data/ab_test/results.json') as f:
        results = json.load(f)

    with open('/opt/airflow/data/model/metrics.json') as f:
        model_metrics = json.load(f)

    alerts = []

    # Проверка read rate в контроле
    control_rate = results['control_read_rate']
    if control_rate < READ_RATE_THRESHOLD:
        alerts.append(
            f"⚠️ *Низкий read rate*\n"
            f"Контроль: {control_rate:.2%}\n"
            f"Порог: {READ_RATE_THRESHOLD:.2%}"
        )

    # Проверка uplift
    uplift = results['uplift_relative']
    if uplift < 0.05:  # менее 5% — модель плохо работает
        alerts.append(
            f"⚠️ *Низкий uplift*\n"
            f"Uplift: {uplift:+.2%}\n"
            f"Порог: +5%"
        )

    # Проверка значимости
    if not results['significant']:
        alerts.append(
            f"⚠️ *A/B-тест не значим*\n"
            f"p-value: {results['p_value']:.4f}"
        )

    # Проверка качества модели
    roc_auc = model_metrics['roc_auc']
    if roc_auc < 0.6:
        alerts.append(
            f"⚠️ *Деградация модели*\n"
            f"ROC-AUC: {roc_auc:.4f}\n"
            f"Порог: 0.6"
        )

    if not alerts:
        message = (
            f"✅ *Все метрики в норме*\n\n"
            f"Read rate (control): {control_rate:.2%}\n"
            f"Read rate (test): {results['test_read_rate']:.2%}\n"
            f"Uplift: {uplift:+.2%}\n"
            f"p-value: {results['p_value']:.4f}\n"
            f"ROC-AUC: {roc_auc:.4f}"
        )
    else:
        message = "\n\n".join(alerts)

    print(message)
    send_telegram(message)


if __name__ == '__main__':
    check_metrics()
