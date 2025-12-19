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
        "`docker compose up -d` (см. шаги 1–2 в task1.md)."
    )
    ensure_connection()

    steps = [
        (
            "Шаг 3",
            "Обновление статистики таблицы",
            "ANALYZE t_books;",
        ),
        (
            "Шаг 4",
            "Создание BRIN индекса по category",
            "CREATE INDEX IF NOT EXISTS t_books_brin_cat_idx ON t_books USING brin(category);",
        ),
        (
            "Шаг 5",
            "План поиска строк с NULL category",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_books WHERE category IS NULL;
            """,
        ),
        (
            "Шаг 6",
            "Создание BRIN индекса по author",
            "CREATE INDEX IF NOT EXISTS t_books_brin_author_idx ON t_books USING brin(author);",
        ),
        (
            "Шаг 7",
            "План поиска по category='INDEX' и author='SYSTEM'",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_books 
            WHERE category = 'INDEX' AND author = 'SYSTEM';
            """,
        ),
        (
            "Шаг 8",
            "План получения списка уникальных категорий",
            """
            EXPLAIN ANALYZE
            SELECT DISTINCT category 
            FROM t_books 
            ORDER BY category;
            """,
        ),
        (
            "Шаг 9",
            "План подсчета книг с автором на 'S%'",
            """
            EXPLAIN ANALYZE
            SELECT COUNT(*) 
            FROM t_books 
            WHERE author LIKE 'S%';
            """,
        ),
        (
            "Шаг 10",
            "Создание индекса для регистронезависимого поиска по title",
            "CREATE INDEX IF NOT EXISTS t_books_lower_title_idx ON t_books(LOWER(title));",
        ),
        (
            "Шаг 11",
            "План подсчета книг, где title начинается на 'o'",
            """
            EXPLAIN ANALYZE
            SELECT COUNT(*) 
            FROM t_books 
            WHERE LOWER(title) LIKE 'o%';
            """,
        ),
        (
            "Шаг 12",
            "Удаление созданных BRIN и функционального индекса",
            """
            DROP INDEX IF EXISTS t_books_brin_cat_idx;
            DROP INDEX IF EXISTS t_books_brin_author_idx;
            DROP INDEX IF EXISTS t_books_lower_title_idx;
            """,
        ),
        (
            "Шаг 13",
            "Создание составного BRIN индекса category+author",
            """
            CREATE INDEX IF NOT EXISTS t_books_brin_cat_auth_idx ON t_books 
            USING brin(category, author);
            """,
        ),
        (
            "Шаг 14",
            "Повторный план поиска по category='INDEX' и author='SYSTEM'",
            """
            EXPLAIN ANALYZE
            SELECT * FROM t_books 
            WHERE category = 'INDEX' AND author = 'SYSTEM';
            """,
        ),
    ]

    for step_label, description, sql in steps:
        run_sql(step_label, description, sql)


if __name__ == "__main__":
    main()
