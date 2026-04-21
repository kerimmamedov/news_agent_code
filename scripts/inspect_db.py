from app.db.connection import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, current_schema();")
            print("\n=== DB INFO ===")
            print(cur.fetchone())

            print("\n=== TABLES ===")
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            for row in tables:
                print(row[0])

            print("\n=== COLUMNS ===")
            cur.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            rows = cur.fetchall()

            current_table = None
            for table_name, column_name, data_type in rows:
                if table_name != current_table:
                    current_table = table_name
                    print(f"\n[{table_name}]")
                print(f" - {column_name}: {data_type}")


if __name__ == "__main__":
    main()