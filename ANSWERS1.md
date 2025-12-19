```
python run_all.py
Перед запуском убедитесь, что контейнер поднят командой `docker compose up -d` (см. шаги 1–2 в task1.md).

=== Проверка соединения: Тестовое подключение к БД и вывод версии ===
SQL:
SELECT version();
Результат:
version                                         
-----------------------------------------------------------------------------------------
 PostgreSQL 17.7 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
(1 row)

=== Шаг 3: Обновление статистики таблицы ===
SQL:
ANALYZE t_books;
Результат:
ANALYZE

=== Шаг 4: Создание BRIN индекса по category ===
SQL:
CREATE INDEX IF NOT EXISTS t_books_brin_cat_idx ON t_books USING brin(category);
Результат:
CREATE INDEX

=== Шаг 5: План поиска строк с NULL category ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_books WHERE category IS NULL;
Результат:
QUERY PLAN                                                          
------------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on t_books  (cost=12.00..16.01 rows=1 width=33) (actual time=0.021..0.021 rows=0 loops=1)
   Recheck Cond: (category IS NULL)
   ->  Bitmap Index Scan on t_books_brin_cat_idx  (cost=0.00..12.00 rows=1 width=0) (actual time=0.015..0.015 rows=0 loops=1)
         Index Cond: (category IS NULL)
 Planning Time: 0.843 ms
 Execution Time: 0.102 ms
(6 rows)

=== Шаг 6: Создание BRIN индекса по author ===
SQL:
CREATE INDEX IF NOT EXISTS t_books_brin_author_idx ON t_books USING brin(author);
Результат:
CREATE INDEX

=== Шаг 7: План поиска по category='INDEX' и author='SYSTEM' ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_books 
WHERE category = 'INDEX' AND author = 'SYSTEM';
Результат:
QUERY PLAN                                                              
--------------------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on t_books  (cost=12.15..2311.86 rows=1 width=33) (actual time=21.422..21.423 rows=0 loops=1)
   Recheck Cond: ((category)::text = 'INDEX'::text)
   Rows Removed by Index Recheck: 150000
   Filter: ((author)::text = 'SYSTEM'::text)
   Heap Blocks: lossy=1225
   ->  Bitmap Index Scan on t_books_brin_cat_idx  (cost=0.00..12.15 rows=71647 width=0) (actual time=0.224..0.224 rows=12250 loops=1)
         Index Cond: ((category)::text = 'INDEX'::text)
 Planning Time: 1.650 ms
 Execution Time: 21.529 ms
(9 rows)

=== Шаг 8: План получения списка уникальных категорий ===
SQL:
EXPLAIN ANALYZE
SELECT DISTINCT category 
FROM t_books 
ORDER BY category;
Результат:
QUERY PLAN                                                         
---------------------------------------------------------------------------------------------------------------------------
 Sort  (cost=3100.11..3100.12 rows=5 width=7) (actual time=43.399..43.400 rows=6 loops=1)
   Sort Key: category
   Sort Method: quicksort  Memory: 25kB
   ->  HashAggregate  (cost=3100.00..3100.05 rows=5 width=7) (actual time=43.311..43.312 rows=6 loops=1)
         Group Key: category
         Batches: 1  Memory Usage: 24kB
         ->  Seq Scan on t_books  (cost=0.00..2725.00 rows=150000 width=7) (actual time=0.011..10.874 rows=150000 loops=1)
 Planning Time: 1.526 ms
 Execution Time: 43.660 ms
(9 rows)

=== Шаг 9: План подсчета книг с автором на 'S%' ===
SQL:
EXPLAIN ANALYZE
SELECT COUNT(*) 
FROM t_books 
WHERE author LIKE 'S%';
Результат:
QUERY PLAN                                                  
-------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=3100.03..3100.05 rows=1 width=8) (actual time=21.540..21.541 rows=1 loops=1)
   ->  Seq Scan on t_books  (cost=0.00..3100.00 rows=14 width=0) (actual time=21.534..21.534 rows=0 loops=1)
         Filter: ((author)::text ~~ 'S%'::text)
         Rows Removed by Filter: 150000
 Planning Time: 1.661 ms
 Execution Time: 21.668 ms
(6 rows)

=== Шаг 10: Создание индекса для регистронезависимого поиска по title ===
SQL:
CREATE INDEX IF NOT EXISTS t_books_lower_title_idx ON t_books(LOWER(title));
Результат:
CREATE INDEX

=== Шаг 11: План подсчета книг, где title начинается на 'o' ===
SQL:
EXPLAIN ANALYZE
SELECT COUNT(*) 
FROM t_books 
WHERE LOWER(title) LIKE 'o%';
Результат:
QUERY PLAN                                                  
--------------------------------------------------------------------------------------------------------------
 Aggregate  (cost=3476.88..3476.89 rows=1 width=8) (actual time=51.408..51.409 rows=1 loops=1)
   ->  Seq Scan on t_books  (cost=0.00..3475.00 rows=750 width=0) (actual time=51.401..51.403 rows=1 loops=1)
         Filter: (lower((title)::text) ~~ 'o%'::text)
         Rows Removed by Filter: 149999
 Planning Time: 1.905 ms
 Execution Time: 51.526 ms
(6 rows)

=== Шаг 12: Удаление созданных BRIN и функционального индекса ===
SQL:
DROP INDEX IF EXISTS t_books_brin_cat_idx;
DROP INDEX IF EXISTS t_books_brin_author_idx;
DROP INDEX IF EXISTS t_books_lower_title_idx;
Результат:
DROP INDEX
DROP INDEX
DROP INDEX

=== Шаг 13: Создание составного BRIN индекса category+author ===
SQL:
CREATE INDEX IF NOT EXISTS t_books_brin_cat_auth_idx ON t_books 
USING brin(category, author);
Результат:
CREATE INDEX

=== Шаг 14: Повторный план поиска по category='INDEX' и author='SYSTEM' ===
SQL:
EXPLAIN ANALYZE
SELECT * FROM t_books 
WHERE category = 'INDEX' AND author = 'SYSTEM';
Результат:
QUERY PLAN                                                                
-----------------------------------------------------------------------------------------------------------------------------------------
 Bitmap Heap Scan on t_books  (cost=12.15..2311.86 rows=1 width=33) (actual time=1.937..1.938 rows=0 loops=1)
   Recheck Cond: (((category)::text = 'INDEX'::text) AND ((author)::text = 'SYSTEM'::text))
   Rows Removed by Index Recheck: 8847
   Heap Blocks: lossy=73
   ->  Bitmap Index Scan on t_books_brin_cat_auth_idx  (cost=0.00..12.15 rows=71647 width=0) (actual time=0.209..0.210 rows=730 loops=1)
         Index Cond: (((category)::text = 'INDEX'::text) AND ((author)::text = 'SYSTEM'::text))
 Planning Time: 2.000 ms
 Execution Time: 2.044 ms
(8 rows)
```