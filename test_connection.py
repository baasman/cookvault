try:
    import psycopg

    print("✅ psycopg3 imported successfully")

    # Test connection
    conn = psycopg.connect(
        "postgresql://cookvault_admin:pXRJhZYhbCJ1pnL3Q5ZJ4qUaUryDcJRB@dpg-d1rfd6qli9vc73b5tmq0-a.oregon-postgres.render.com:5432/cookvault"
    )
    print("✅ Database connection successful")

    # Test a simple query
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        version = cur.fetchone()
        print(f"✅ PostgreSQL version: {version[0]}")

    conn.close()

except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Connection error: {e}")
