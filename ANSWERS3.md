```
python run_all3.py
Перед запуском убедитесь, что контейнер поднят командой `docker compose up -d` (см. шаги 1–2).

=== Проверка соединения: Тестовое подключение к БД и вывод версии ===
SQL:
SELECT version();
Результат:
version                                         
-----------------------------------------------------------------------------------------
 PostgreSQL 17.7 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
(1 row)

=== Шаг 1: Создание таблицы test_cluster с 1 млн строк ===
SQL:
DROP TABLE IF EXISTS test_cluster CASCADE;
CREATE TABLE test_cluster AS 
SELECT 
    generate_series(1,1000000) as id,
    CASE WHEN random() < 0.5 THEN 'A' ELSE 'B' END as category,
    md5(random()::text) as data;
Результат:
NOTICE:  table "test_cluster" does not exist, skipping
DROP TABLE
SELECT 1000000

=== Шаг 2: Создание индекса по category ===
SQL:
CREATE INDEX IF NOT EXISTS test_cluster_cat_idx ON test_cluster(category);
Результат:
CREATE INDEX

=== Шаг 3: План запроса до кластеризации (category = 'A') ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM test_cluster WHERE category = 'A';
Результат:
QUERY PLAN                                                               
----------------------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on test_cluster  (cost=59.17..7696.73 rows=5000 width=68) (actual time=23.493..120.171 rows=500163 loops=1)
   Recheck Cond: (category = 'A'::text)
   Heap Blocks: exact=8334
   ->  Bitmap Index Scan on test_cluster_cat_idx  (cost=0.00..57.92 rows=5000 width=0) (actual time=22.341..22.345 rows=500163 loops=1)
         Index Cond: (category = 'A'::text)
 Planning Time: 1.303 ms
 Execution Time: 133.961 ms
(7 rows)

=== Шаг 4: Кластеризация таблицы по индексу test_cluster_cat_idx ===
SQL:
CLUSTER test_cluster USING test_cluster_cat_idx;
Результат:
CLUSTER

=== Шаг 5: План запроса после кластеризации (category = 'A') ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM test_cluster WHERE category = 'A';
Результат:
QUERY PLAN                                                               
----------------------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on test_cluster  (cost=59.17..7668.56 rows=5000 width=68) (actual time=12.448..67.591 rows=500163 loops=1)
   Recheck Cond: (category = 'A'::text)
   Heap Blocks: exact=4169
   ->  Bitmap Index Scan on test_cluster_cat_idx  (cost=0.00..57.92 rows=5000 width=0) (actual time=11.992..11.993 rows=500163 loops=1)
         Index Cond: (category = 'A'::text)
 Planning Time: 0.726 ms
 Execution Time: 81.672 ms
(7 rows)
```