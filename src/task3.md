## Задание 3

1. Создайте таблицу с большим количеством данных:
    ```sql
    CREATE TABLE test_cluster AS 
    SELECT 
        generate_series(1,1000000) as id,
        CASE WHEN random() < 0.5 THEN 'A' ELSE 'B' END as category,
        md5(random()::text) as data;
    ```

2. Создайте индекс:
    ```sql
    CREATE INDEX test_cluster_cat_idx ON test_cluster(category);
    ```

3. Измерьте производительность до кластеризации:
    ```sql
    EXPLAIN ANALYZE
    SELECT * FROM test_cluster WHERE category = 'A';
    ```
    
    *План выполнения:*
    ```
    Bitmap Heap Scan on test_cluster  (cost=59.17..7696.73 rows=5000 width=68) (actual time=23.493..120.171 rows=500163 loops=1)
      Recheck Cond: (category = 'A'::text)
      Heap Blocks: exact=8334
      ->  Bitmap Index Scan on test_cluster_cat_idx  (cost=0.00..57.92 rows=5000 width=0) (actual time=22.341..22.345 rows=500163 loops=1)
            Index Cond: (category = 'A'::text)
    Planning Time: 1.303 ms
    Execution Time: 133.961 ms
    ```
    
    *Объясните результат:*
    Bitmap Index Scan по индексу на category находит ~500k строк (значение 'A' встречается часто), Bitmap Heap Scan читает 8334 блоков. Время ~134 мс из-за большого объема данных и неупорядоченной кучи.

4. Выполните кластеризацию:
    ```sql
    CLUSTER test_cluster USING test_cluster_cat_idx;
    ```
    
    *Результат:*
    CLUSTER

5. Измерьте производительность после кластеризации:
    ```sql
    EXPLAIN ANALYZE
    SELECT * FROM test_cluster WHERE category = 'A';
    ```
    
    *План выполнения:*
    ```
    Bitmap Heap Scan on test_cluster  (cost=59.17..7668.56 rows=5000 width=68) (actual time=12.448..67.591 rows=500163 loops=1)
      Recheck Cond: (category = 'A'::text)
      Heap Blocks: exact=4169
      ->  Bitmap Index Scan on test_cluster_cat_idx  (cost=0.00..57.92 rows=5000 width=0) (actual time=11.992..11.993 rows=500163 loops=1)
            Index Cond: (category = 'A'::text)
    Planning Time: 0.726 ms
    Execution Time: 81.672 ms
    ```
    
    *Объясните результат:*
    После кластеризации строки с одинаковой категорией лежат ближе; Bitmap Heap Scan читает меньше блоков (4169 вместо 8334), время падает до ~82 мс. Индекс и план те же, выигрывает за счет физической близости данных.

6. Сравните производительность до и после кластеризации:
    
    *Сравнение:*
    Время выполнения снизилось примерно с 134 мс до 82 мс, число читаемых блоков уменьшилось вдвое (8334 → 4169). Кластеризация улучшила локальность данных и ускорила выборку, хотя план остался Bitmap Heap Scan.
