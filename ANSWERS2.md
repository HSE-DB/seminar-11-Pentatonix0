```
python run_all2.py
Перед запуском убедитесь, что контейнер поднят командой `docker compose up -d` (см. шаги 1–2 в task2.md).

=== Проверка соединения: Тестовое подключение к БД и вывод версии ===
SQL:
SELECT version();
Результат:
version                                         
-----------------------------------------------------------------------------------------
 PostgreSQL 17.7 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
(1 row)

=== Шаг 3: Обновление статистики t_books ===
SQL:
ANALYZE t_books;
Результат:
ANALYZE

=== Шаг 4: Создание полнотекстового GIN-индекса по title ===
SQL:
CREATE INDEX IF NOT EXISTS t_books_fts_idx ON t_books 
USING GIN (to_tsvector('english', title));
Результат:
CREATE INDEX

=== Шаг 5: План поиска книг со словом 'expert' ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_books 
WHERE to_tsvector('english', title) @@ to_tsquery('english', 'expert');
Результат:
QUERY PLAN                                                         
---------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on t_books  (cost=21.03..1336.08 rows=750 width=33) (actual time=0.030..0.031 rows=1 loops=1)
   Recheck Cond: (to_tsvector('english'::regconfig, (title)::text) @@ '''expert'''::tsquery)
   Heap Blocks: exact=1
   ->  Bitmap Index Scan on t_books_fts_idx  (cost=0.00..20.84 rows=750 width=0) (actual time=0.019..0.019 rows=1 loops=1)
         Index Cond: (to_tsvector('english'::regconfig, (title)::text) @@ '''expert'''::tsquery)
 Planning Time: 1.917 ms
 Execution Time: 0.105 ms
(7 rows)

=== Шаг 6: Удаление полнотекстового индекса ===
SQL:
DROP INDEX IF EXISTS t_books_fts_idx;
Результат:
DROP INDEX

=== Шаг 7: Создание таблицы t_lookup ===
SQL:
DROP TABLE IF EXISTS t_lookup CASCADE;
CREATE TABLE t_lookup (
     item_key VARCHAR(10) NOT NULL,
     item_value VARCHAR(100)
);
Результат:
NOTICE:  table "t_lookup" does not exist, skipping
DROP TABLE
CREATE TABLE

=== Шаг 8: Добавление первичного ключа t_lookup ===
SQL:
ALTER TABLE t_lookup 
ADD CONSTRAINT t_lookup_pk PRIMARY KEY (item_key);
Результат:
ALTER TABLE

=== Шаг 9: Заполнение t_lookup 150000 строками ===
SQL:
INSERT INTO t_lookup 
SELECT 
     LPAD(CAST(generate_series(1, 150000) AS TEXT), 10, '0'),
     'Value_' || generate_series(1, 150000);
Результат:
INSERT 0 150000

=== Шаг 10: Создание таблицы t_lookup_clustered ===
SQL:
DROP TABLE IF EXISTS t_lookup_clustered CASCADE;
CREATE TABLE t_lookup_clustered (
     item_key VARCHAR(10) PRIMARY KEY,
     item_value VARCHAR(100)
);
Результат:
NOTICE:  table "t_lookup_clustered" does not exist, skipping
DROP TABLE
CREATE TABLE

=== Шаг 11: Заполнение t_lookup_clustered и кластеризация по PK ===
SQL:
INSERT INTO t_lookup_clustered 
SELECT * FROM t_lookup;

CLUSTER t_lookup_clustered USING t_lookup_clustered_pkey;
Результат:
INSERT 0 150000
CLUSTER

=== Шаг 12: Обновление статистики lookup-таблиц ===
SQL:
ANALYZE t_lookup;
ANALYZE t_lookup_clustered;
Результат:
ANALYZE
ANALYZE

=== Шаг 13: План поиска по ключу в t_lookup ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_lookup WHERE item_key = '0000000455';
Результат:
QUERY PLAN                                                       
-----------------------------------------------------------------------------------------------------------------------
 Index Scan using t_lookup_pk on t_lookup  (cost=0.42..8.44 rows=1 width=23) (actual time=0.029..0.030 rows=1 loops=1)
   Index Cond: ((item_key)::text = '0000000455'::text)
 Planning Time: 0.653 ms
 Execution Time: 0.073 ms
(4 rows)

=== Шаг 14: План поиска по ключу в t_lookup_clustered ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_lookup_clustered WHERE item_key = '0000000455';
Результат:
QUERY PLAN                                                                  
---------------------------------------------------------------------------------------------------------------------------------------------
 Index Scan using t_lookup_clustered_pkey on t_lookup_clustered  (cost=0.42..8.44 rows=1 width=23) (actual time=0.042..0.042 rows=1 loops=1)
   Index Cond: ((item_key)::text = '0000000455'::text)
 Planning Time: 0.672 ms
 Execution Time: 0.085 ms
(4 rows)

=== Шаг 15: Создание индекса item_value для t_lookup ===
SQL:
CREATE INDEX IF NOT EXISTS t_lookup_value_idx ON t_lookup(item_value);
Результат:
CREATE INDEX

=== Шаг 16: Создание индекса item_value для t_lookup_clustered ===
SQL:
CREATE INDEX IF NOT EXISTS t_lookup_clustered_value_idx 
ON t_lookup_clustered(item_value);
Результат:
CREATE INDEX

=== Шаг 17: План поиска по item_value в t_lookup ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_lookup WHERE item_value = 'T_BOOKS';
Результат:
QUERY PLAN                                                          
------------------------------------------------------------------------------------------------------------------------------
 Index Scan using t_lookup_value_idx on t_lookup  (cost=0.42..8.44 rows=1 width=23) (actual time=0.068..0.068 rows=0 loops=1)
   Index Cond: ((item_value)::text = 'T_BOOKS'::text)
 Planning Time: 1.267 ms
 Execution Time: 0.147 ms
(4 rows)

=== Шаг 18: План поиска по item_value в t_lookup_clustered ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_lookup_clustered WHERE item_value = 'T_BOOKS';
Результат:
QUERY PLAN                                                                    
--------------------------------------------------------------------------------------------------------------------------------------------------
 Index Scan using t_lookup_clustered_value_idx on t_lookup_clustered  (cost=0.42..8.44 rows=1 width=23) (actual time=0.060..0.061 rows=0 loops=1)
   Index Cond: ((item_value)::text = 'T_BOOKS'::text)
 Planning Time: 1.332 ms
 Execution Time: 0.128 ms
(4 rows)
```