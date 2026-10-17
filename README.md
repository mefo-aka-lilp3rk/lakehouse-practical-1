# Практическая работа №1 — локальный Lakehouse

**Автор:** Вдовин Никита Михайлович
**Вариант:** 1, TPC-H Q3 «Shipping Priority»
**Масштаб:** `sf1` — около 1 ГБ исходных данных TPC-H; подходит для локального Docker Desktop и даёт измеримый конвейер без чрезмерной нагрузки на ноутбук.

Решение строит локальный Lakehouse на Iceberg: Silo (совместимая с MinIO сборка) хранит файлы, PostgreSQL хранит метаданные Lakekeeper, Lakekeeper выступает Iceberg REST Catalog, Trino выполняет SQL, а Apache Superset показывает Bronze. Данные TPC-H детерминированно генерируются коннектором Trino, отдельно скачивать датасет не нужно.

> В исходной методичке показан MinIO. Его исходный образ не удалось загрузить из используемой среды, поэтому используется Silo — поддерживаемая сборка на основе MinIO с S3 API и STS. Lakekeeper включает Silo в собственный локальный пример Iceberg REST Catalog. Trino и Lakekeeper обращаются к нему по S3 API.

## Состав проекта

- `docker-compose.yml` — PostgreSQL, Silo, Lakekeeper, Trino и Superset.
- `trino/` — конфигурация Trino с источником TPC-H и каталогом Iceberg.
- `lakekeeper/` — настройки Iceberg warehouse.
- `sql/00–04` — создание схем и поток Bronze → Silver → Gold, проверки и размеры файлов.
- `sql/05–06` — изолированные демонстрации schema evolution и восстановления Iceberg snapshot.
- `scripts/demo_time_travel.py` — автоматический тест чтения версии и возврата snapshot на отдельной demo-таблице.
- `scripts/run_pipeline.sh` — последовательный запуск SQL конвейера.
- `scripts/verify_q3.py` — сверка Gold с исходным запросом TPC-H Q3.
- `scripts/benchmark.py` — замеры PARQUET/ORC и GZIP/ZSTD, объёма файлов и времени Q3.
- `scripts/setup_superset_dashboard.py` — регистрация Gold-витрины, таблицы и дашборда в Superset.
- `report.md` — отчёт с методикой, результатами и выводами.

## Требования

- Docker Desktop с работающим Docker Compose v2.
- Git и Python 3 (без дополнительных Python-пакетов).
- Для выбранной конфигурации Docker Desktop выделено около 8 ГБ памяти; Superset лучше запускать отдельно после SQL-конвейера и benchmark.

## Запуск

```bash
cp .env.example .env
docker compose pull
docker compose up -d postgres object-store object-store-init lakekeeper-migrate lakekeeper lakekeeper-init trino
```

Дождитесь успешной инициализации сервисов:

```bash
docker compose ps -a
docker compose logs --tail=80 lakekeeper trino
```

Создайте Bronze, Silver и Gold и выполните проверки:

```bash
./scripts/run_pipeline.sh
```

Результаты и размеры Iceberg-файлов выводятся в терминал. Для повторного запуска после первичного создания таблиц удалите старые схемы в Trino или сбросьте тестовые контейнеры и тома (`docker compose down -v` удаляет локальные учебные данные).

Запустите сравнение форматов и кодеков:

```bash
python3 scripts/benchmark.py
```

Таблица результатов появится в `benchmark/results.csv`. Скрипт повторяет каждую агрегацию трижды после прогрева, сравнивает строки результата для всех конфигураций и сохраняет медианное время. Для сопоставимости запускайте на одном компьютере, при одинаковом масштабе и без других тяжёлых процессов.

### Superset: Bronze и Gold

```bash
docker compose up -d --build superset
```

Откройте `http://localhost:8088` и войдите с учётной записью `admin`, паролем из `.env` (`SUPERSET_ADMIN_PASSWORD`). В **Settings → Database Connections → + Database** выберите Trino и задайте SQLAlchemy URI:

```text
trino://admin@trino:8080/iceberg/bronze
```

Создайте dataset из `bronze.customer`, `bronze.orders` или `bronze.lineitem`. Так Superset читает именно Bronze через Trino; BI-сервис не получает прямого доступа к файлам object store.

В SQL Lab проверьте Bronze запросом `SELECT custkey, mktsegment FROM bronze.customer ORDER BY custkey LIMIT 5`. Чтобы создать дашборд поверх итоговой витрины Gold, выполните:

```bash
python3 scripts/setup_superset_dashboard.py
```

Скрипт использует пароль администратора из переменной `SUPERSET_ADMIN_PASSWORD`, файла `.env` или стандартное локальное значение из Compose. Он создаёт dataset `gold.q3_shipping_priority`, табличную визуализацию и дашборд `TPC-H Q3 — Gold`; повторный запуск не создаёт дубликаты. Дашборд доступен по адресу `http://localhost:8088/superset/dashboard/1/` (ID может отличаться, скрипт печатает фактическую ссылку).

### Schema evolution и time travel

После основного конвейера выполните:

```bash
python3 scripts/run_sql.py sql/05_schema_evolution.sql
python3 scripts/demo_time_travel.py
```

Скрипт time travel автоматически создаёт отдельную таблицу на 20 строк, сохраняет ID её снимка, добавляет 5 строк, читает прежнюю версию через `FOR VERSION AS OF`, затем выполняет `ALTER TABLE ... EXECUTE rollback_to_snapshot(...)` и проверяет возврат к 20 строкам. При повторном запуске он удаляет и заново создаёт только `silver.time_travel_demo`; основные таблицы Silver остаются нетронутыми. `sql/06_time_travel.sql` содержит эквивалентные SQL-команды для ручного пошагового просмотра.

## Модель данных

- **Bronze:** нужные Q3 колонки исходных `customer`, `orders`, `lineitem`.
- **Silver:** очищенный сегмент клиента, типизированные даты/ключи, соединённые строки заказа и вычисленная скидочная выручка строки; сохранены строки, подходящие под фильтры Q3.
- **Gold:** десять заказов с максимальной выручкой и полями `orderkey`, `revenue`, `orderdate`, `shippriority`.
- Во всех слоях пока используется PARQUET/ZSTD. В benchmark физически создаются отдельные Bronze-копии для PARQUET/ORC и GZIP/ZSTD; результаты Gold сравниваются между конфигурациями.

## Ограничения и повторяемость

- Учебные учётные данные из `.env.example` предназначены только для локального запуска; не публикуйте `.env` и не открывайте порты в публичную сеть.
- Если меняете `S3_ACCESS_KEY` или `S3_SECRET_KEY` в `.env`, задайте те же значения в `trino/catalog/iceberg.properties` перед запуском.
- Конвейер рассчитан на чистую схему. Для полного сброса тестового окружения используйте `docker compose down -v`, затем повторите запуск. Эта команда удаляет все данные именованных томов проекта.
- Репозиторий не включает файл со списком студентов `вариант.xlsx`.
- Порты: Silo/MinIO API `9000`, консоль `9001`, Lakekeeper `8181`, Trino `8080`, Superset `8088`.
