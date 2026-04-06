# New Processing Transfer Suite

Изолированный live-suite для нового процессинга переводов.

Этот набор живет отдельно от корневых `tests/` и `jobs/`:
- не импортирует код из корня репозитория;
- использует собственные helper-модули, proto и data-файлы;
- запускается только при `RUN_LIVE_NEW_PROCESSING=1`.
- перестраивает route-матрицу из локального catalog внутри suite.

## Покрытие v1

- `MAKE_BANK_CLIENT_TRANSFER`
  - `card_to_card`
  - `account_to_card`
  - `card_to_account`
  - `account_to_account`
- `MAKE_OWN_ACCOUNTS_TRANSFER`
  - `same_currency`
  - `fx`
- `MAKE_OTHER_BANK_TRANSFER`
  - `clearing`
  - `gross`
- `MAKE_QR_PAYMENT`
  - `static_qr`

Не входят в активный v1:
- `MAKE_SWIFT_TRANSFER`
- `MAKE_IPC_CARD_TRANSFER`

## Структура

- `contracts/main.js` — локальная копия контракта маршрутов
- `proto/` — локальные proto и gRPC stubs
- `support/` — изолированное ядро suite
- `data/catalog/` — source-of-truth для счетов, карт и route fixtures
- `data/` — generated route-матрицы по отдельным JSON
- `tests/` — исполняемые live-тесты

## Настройка

1. Из папки suite:

```bash
cd /Users/ataiyrysbekov/Documents/GitHub/Backend_api_tests/new_processing_transfer_suite
```

2. Установить зависимости:

```bash
pip install -r requirements.txt
```

3. Подготовить env:

```bash
cp .env.example .env
```

4. Запуск:

```bash
RUN_LIVE_NEW_PROCESSING=1 pytest
```

5. При необходимости вручную пересобрать route JSON из catalog:

```bash
python -m support.matrix_builder
```

## Источник bootstrap-данных

Начальные валидные кейсы взяты из:
- `/Users/ataiyrysbekov/Documents/GitHub/Backend_api_tests/tests/testdata/bank_client_transfer_cases.json`
- `/Users/ataiyrysbekov/Documents/GitHub/Backend_api_tests/data.py`

Дальнейшая замена на другой набор данных должна требовать только замены JSON-файлов в `data/`.
