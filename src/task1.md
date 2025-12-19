# Задание 1: BRIN индексы и bitmap-сканирование

1. Удалите старую базу данных, если есть:
   ```shell
   docker compose down
   ```

2. Поднимите базу данных из src/docker-compose.yml:
   ```shell
   docker compose down && docker compose up -d
   ```

3. Обновите статистику:
   ```sql
   ANALYZE t_books;
   ```

4. Создайте BRIN индекс по колонке category:
   ```sql
   CREATE INDEX t_books_brin_cat_idx ON t_books USING brin(category);
   ```

5. Найдите книги с NULL значением category:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM t_books WHERE category IS NULL;
   ```
   
   *План выполнения:*
   ```
   Bitmap Heap Scan on t_books  (cost=12.00..16.01 rows=1 width=33) (actual time=0.021..0.021 rows=0 loops=1)
     Recheck Cond: (category IS NULL)
     ->  Bitmap Index Scan on t_books_brin_cat_idx  (cost=0.00..12.00 rows=1 width=0) (actual time=0.015..0.015 rows=0 loops=1)
           Index Cond: (category IS NULL)
   Planning Time: 0.843 ms
   Execution Time: 0.102 ms
   ```
   
   *Объясните результат:*
   BRIN-индекс по `category` даёт Bitmap Index Scan даже для NULL. Совпадений нет, поэтому Bitmap Heap Scan не извлекает строк; время минимальное (~0.1 мс), recheck проходит без попаданий.

6. Создайте BRIN индекс по автору:
   ```sql
   CREATE INDEX t_books_brin_author_idx ON t_books USING brin(author);
   ```

7. Выполните поиск по категории и автору:
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM t_books 
   WHERE category = 'INDEX' AND author = 'SYSTEM';
   ```
   
   *План выполнения:*
   ```
   Bitmap Heap Scan on t_books  (cost=12.15..2311.86 rows=1 width=33) (actual time=21.422..21.423 rows=0 loops=1)
     Recheck Cond: ((category)::text = 'INDEX'::text)
     Rows Removed by Index Recheck: 150000
     Filter: ((author)::text = 'SYSTEM'::text)
     Heap Blocks: lossy=1225
     ->  Bitmap Index Scan on t_books_brin_cat_idx  (cost=0.00..12.15 rows=71647 width=0) (actual time=0.224..0.224 rows=12250 loops=1)
           Index Cond: ((category)::text = 'INDEX'::text)
   Planning Time: 1.650 ms
   Execution Time: 21.529 ms
   ```
   
   *Объясните результат (обратите внимание на bitmap scan):*
   BRIN по `category` возвращает множество страниц (bitmap lossy: 1225 блоков, ~150k строк к пересмотру). Фильтр по `author` применяется после, совпадений нет. Из-за большого количества страниц план медленнее (~21 мс).

8. Получите список уникальных категорий:
   ```sql
   EXPLAIN ANALYZE
   SELECT DISTINCT category 
   FROM t_books 
   ORDER BY category;
   ```
   
   *План выполнения:*
   ```
   Sort  (cost=3100.11..3100.12 rows=5 width=7) (actual time=43.399..43.400 rows=6 loops=1)
     Sort Key: category
     Sort Method: quicksort  Memory: 25kB
     ->  HashAggregate  (cost=3100.00..3100.05 rows=5 width=7) (actual time=43.311..43.312 rows=6 loops=1)
           Group Key: category
           Batches: 1  Memory Usage: 24kB
           ->  Seq Scan on t_books  (cost=0.00..2725.00 rows=150000 width=7) (actual time=0.011..10.874 rows=150000 loops=1)
   Planning Time: 1.526 ms
   Execution Time: 43.660 ms
   ```
   
   *Объясните результат:*
   Полный Seq Scan собирает все строки, HashAggregate убирает дубликаты категорий (их всего 6), затем сортировка. Индексы не задействованы, так как нужно прочитать всю таблицу для уникальных значений.

9. Подсчитайте книги, где автор начинается на 'S':
   ```sql
   EXPLAIN ANALYZE
   SELECT COUNT(*) 
   FROM t_books 
   WHERE author LIKE 'S%';
   ```
   
   *План выполнения:*
   ```
   Aggregate  (cost=3100.03..3100.05 rows=1 width=8) (actual time=21.540..21.541 rows=1 loops=1)
     ->  Seq Scan on t_books  (cost=0.00..3100.00 rows=14 width=0) (actual time=21.534..21.534 rows=0 loops=1)
           Filter: ((author)::text ~~ 'S%'::text)
           Rows Removed by Filter: 150000
   Planning Time: 1.661 ms
   Execution Time: 21.668 ms
   ```
   
   *Объясните результат:*
   Последовательное сканирование всей таблицы с фильтром `author LIKE 'S%'`; совпадений нет, отфильтровано 150000 строк. BRIN по author не помогает из-за низкой селективности для префикса, поэтому выбран Seq Scan (~21 мс).

10. Создайте индекс для регистронезависимого поиска:
    ```sql
    CREATE INDEX t_books_lower_title_idx ON t_books(LOWER(title));
    ```

11. Подсчитайте книги, начинающиеся на 'O':
    ```sql
   EXPLAIN ANALYZE
   SELECT COUNT(*) 
   FROM t_books 
   WHERE LOWER(title) LIKE 'o%';
   ```
   
   *План выполнения:*
   ```
   Aggregate  (cost=3476.88..3476.89 rows=1 width=8) (actual time=51.408..51.409 rows=1 loops=1)
     ->  Seq Scan on t_books  (cost=0.00..3475.00 rows=750 width=0) (actual time=51.401..51.403 rows=1 loops=1)
           Filter: (lower((title)::text) ~~ 'o%'::text)
           Rows Removed by Filter: 149999
   Planning Time: 1.905 ms
   Execution Time: 51.526 ms
   ```
   
   *Объясните результат:*
   Условие по `LOWER(title)` выполняется через Seq Scan: функциональный индекс не выбран (низкая селективность), читается вся таблица. Найдена одна строка, 149999 отфильтрованы; время ~51 мс.

12. Удалите созданные индексы:
    ```sql
    DROP INDEX t_books_brin_cat_idx;
    DROP INDEX t_books_brin_author_idx;
    DROP INDEX t_books_lower_title_idx;
    ```

13. Создайте составной BRIN индекс:
    ```sql
    CREATE INDEX t_books_brin_cat_auth_idx ON t_books 
    USING brin(category, author);
    ```

14. Повторите запрос из шага 7:
    ```sql
   EXPLAIN ANALYZE
   SELECT * FROM t_books 
   WHERE category = 'INDEX' AND author = 'SYSTEM';
   ```
   
   *План выполнения:*
   ```
   Bitmap Heap Scan on t_books  (cost=12.15..2311.86 rows=1 width=33) (actual time=1.937..1.938 rows=0 loops=1)
     Recheck Cond: (((category)::text = 'INDEX'::text) AND ((author)::text = 'SYSTEM'::text))
     Rows Removed by Index Recheck: 8847
     Heap Blocks: lossy=73
     ->  Bitmap Index Scan on t_books_brin_cat_auth_idx  (cost=0.00..12.15 rows=71647 width=0) (actual time=0.209..0.210 rows=730 loops=1)
           Index Cond: (((category)::text = 'INDEX'::text) AND ((author)::text = 'SYSTEM'::text))
   Planning Time: 2.000 ms
   Execution Time: 2.044 ms
   ```
   
   *Объясните результат:*
   Композитный BRIN по `(category, author)` уменьшает число lossy-блоков до 73 (по сравнению с шагом 7), поэтому план быстрее (~2 мс). Совпадений нет, строки отбрасываются на этапе recheck.
