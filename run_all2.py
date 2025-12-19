import os
import subprocess
import sys
import textwrap

# Connection settings can be overridden via environment variables.
DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": os.environ.get("PGPORT", "5432"),
    "dbname": os.environ.get("PGDATABASE", "workshop"),
    "user": os.environ.get("PGUSER", "student"),
    "password": os.environ.get("PGPASSWORD", "student"),
}


def run_sql(step_label: str, description: str, sql: str) -> None:
    """Execute a SQL snippet with psql and print the captured output."""
    print(f"\n=== {step_label}: {description} ===")
    sql = textwrap.dedent(sql).strip()
    print("SQL:")
    print(sql)
    cmd = [
        "psql",
        "-h",
        DB_CONFIG["host"],
        "-p",
        DB_CONFIG["port"],
        "-U",
        DB_CONFIG["user"],
        "-d",
        DB_CONFIG["dbname"],
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-P",
        "pager=off",
        "-c",
        sql,
    ]
    env = {**os.environ, "PGPASSWORD": DB_CONFIG["password"]}
    try:
        output = subprocess.check_output(
            cmd, text=True, stderr=subprocess.STDOUT, env=env
        )
    except subprocess.CalledProcessError as exc:
        print("Ошибка при выполнении запроса:")
        print(exc.output)
        sys.exit(exc.returncode)

    output = output.strip()
    print("Результат:")
    print(output or "<пустой вывод>")


def ensure_connection() -> None:
    """Fail fast with a readable hint if the database is unavailable."""
    try:
        run_sql(
            "Проверка соединения",
            "Тестовое подключение к БД и вывод версии",
            "SELECT version();",
        )
    except SystemExit:
        print(
            "Не удалось подключиться к Postgres. "
            "Убедитесь, что контейнер запущен командой "
            "`docker compose up -d` из корня проекта."
        )
        raise


def main() -> None:
    print(
        "Перед запуском убедитесь, что контейнер поднят командой "
        "`docker compose up -d` (см. шаги 1–2 в task2.md)."
    )
    ensure_connection()

    steps = [
        (
            "Шаг 3",
            "Обновление статистики t_books",
            "ANALYZE t_books;",
        ),
        (
            "Шаг 4",
            "Создание полнотекстового GIN-индекса по title",
            """
            CREATE INDEX IF NOT EXISTS t_books_fts_idx ON t_books 
            USING GIN (to_tsvector('english', title));
            """,
        ),
        (
            "Шаг 5",
            "План поиска книг со словом 'expert'",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_books 
            WHERE to_tsvector('english', title) @@ to_tsquery('english', 'expert');
            """,
        ),
        (
            "Шаг 6",
            "Удаление полнотекстового индекса",
            "DROP INDEX IF EXISTS t_books_fts_idx;",
        ),
        (
            "Шаг 7",
            "Создание таблицы t_lookup",
            """
            DROP TABLE IF EXISTS t_lookup CASCADE;
            CREATE TABLE t_lookup (
                 item_key VARCHAR(10) NOT NULL,
                 item_value VARCHAR(100)
            );
            """,
        ),
        (
            "Шаг 8",
            "Добавление первичного ключа t_lookup",
            """
            ALTER TABLE t_lookup 
            ADD CONSTRAINT t_lookup_pk PRIMARY KEY (item_key);
            """,
        ),
        (
            "Шаг 9",
            "Заполнение t_lookup 150000 строками",
            """
            INSERT INTO t_lookup 
            SELECT 
                 LPAD(CAST(generate_series(1, 150000) AS TEXT), 10, '0'),
                 'Value_' || generate_series(1, 150000);
            """,
        ),
        (
            "Шаг 10",
            "Создание таблицы t_lookup_clustered",
            """
            DROP TABLE IF EXISTS t_lookup_clustered CASCADE;
            CREATE TABLE t_lookup_clustered (
                 item_key VARCHAR(10) PRIMARY KEY,
                 item_value VARCHAR(100)
            );
            """,
        ),
        (
            "Шаг 11",
            "Заполнение t_lookup_clustered и кластеризация по PK",
            """
            INSERT INTO t_lookup_clustered 
            SELECT * FROM t_lookup;
            
            CLUSTER t_lookup_clustered USING t_lookup_clustered_pkey;
            """,
        ),
        (
            "Шаг 12",
            "Обновление статистики lookup-таблиц",
            """
            ANALYZE t_lookup;
            ANALYZE t_lookup_clustered;
            """,
        ),
        (
            "Шаг 13",
            "План поиска по ключу в t_lookup",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_lookup WHERE item_key = '0000000455';
            """,
        ),
        (
            "Шаг 14",
            "План поиска по ключу в t_lookup_clustered",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_lookup_clustered WHERE item_key = '0000000455';
            """,
        ),
        (
            "Шаг 15",
            "Создание индекса item_value для t_lookup",
            "CREATE INDEX IF NOT EXISTS t_lookup_value_idx ON t_lookup(item_value);",
        ),
        (
            "Шаг 16",
            "Создание индекса item_value для t_lookup_clustered",
            """
            CREATE INDEX IF NOT EXISTS t_lookup_clustered_value_idx 
            ON t_lookup_clustered(item_value);
            """,
        ),
        (
            "Шаг 17",
            "План поиска по item_value в t_lookup",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_lookup WHERE item_value = 'T_BOOKS';
            """,
        ),
        (
            "Шаг 18",
            "План поиска по item_value в t_lookup_clustered",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_lookup_clustered WHERE item_value = 'T_BOOKS';
            """,
        ),
    ]

    for step_label, description, sql in steps:
        run_sql(step_label, description, sql)

    print(
        "\n=== Шаг 19: Сравнение ===\n"
        "Сравните планы и время выполнения шагов 17 и 18, чтобы оценить влияние кластеризации."
    )


if __name__ == "__main__":
    main()
