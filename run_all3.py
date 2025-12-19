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
        "`docker compose up -d` (см. шаги 1–2)."
    )
    ensure_connection()

    steps = [
        (
            "Шаг 1",
            "Создание таблицы test_cluster с 1 млн строк",
            """
            DROP TABLE IF EXISTS test_cluster CASCADE;
            CREATE TABLE test_cluster AS 
            SELECT 
                generate_series(1,1000000) as id,
                CASE WHEN random() < 0.5 THEN 'A' ELSE 'B' END as category,
                md5(random()::text) as data;
            """,
        ),
        (
            "Шаг 2",
            "Создание индекса по category",
            "CREATE INDEX IF NOT EXISTS test_cluster_cat_idx ON test_cluster(category);",
        ),
        (
            "Шаг 3",
            "План запроса до кластеризации (category = 'A')",
            """
            EXPLAIN ANALYZE
            SELECT * FROM test_cluster WHERE category = 'A';
            """,
        ),
        (
            "Шаг 4",
            "Кластеризация таблицы по индексу test_cluster_cat_idx",
            "CLUSTER test_cluster USING test_cluster_cat_idx;",
        ),
        (
            "Шаг 5",
            "План запроса после кластеризации (category = 'A')",
            """
            EXPLAIN ANALYZE
            SELECT * FROM test_cluster WHERE category = 'A';
            """,
        ),
    ]

    for step_label, description, sql in steps:
        run_sql(step_label, description, sql)

    print(
        "\n=== Шаг 6: Сравнение ===\n"
        "Сравните выводы шагов 3 и 5 (стоимость, типы сканов, время), чтобы описать эффект кластеризации."
    )


if __name__ == "__main__":
    main()
