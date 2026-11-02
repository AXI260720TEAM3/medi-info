import csv
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

with open("data/dict/symptom_keyword.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(len(rows), "줄 읽음")

conninfo = (
    f"host={os.getenv('DB_HOST')} port={os.getenv('DB_PORT')} "
    f"dbname={os.getenv('DB_NAME')} user={os.getenv('DB_USER')} password={os.getenv('DB_PASS')}"
)

with psycopg.connect(conninfo) as conn:
    for row in rows:
                conn.execute(
            """
            INSERT INTO symptom_keyword (keyword, category, action)
            VALUES (%s, %s, %s)
            ON CONFLICT (keyword) DO UPDATE
            SET category = EXCLUDED.category, action = EXCLUDED.action
            """,
            (row["keyword"], row["category"], row["action"]),
        )

    keywords = [row["keyword"] for row in rows]
    conn.execute("DELETE FROM symptom_keyword WHERE keyword <> ALL(%s)", (keywords,))
    
    count = conn.execute("SELECT count(*) FROM symptom_keyword").fetchone()[0]
    print("넣은 뒤 symptom_keyword 행 수:", count)

    with open("data/dict/caution_keyword.csv", encoding="utf-8-sig") as f:
        caution_rows = list(csv.DictReader(f))

    for row in caution_rows:
        conn.execute(
            """
            INSERT INTO caution_keyword (keyword, target)
            VALUES (%s, %s)
            ON CONFLICT (keyword) DO UPDATE
            SET target = EXCLUDED.target
            """,
            (row["keyword"], row["target"]),
        )

    caution_keywords = [row["keyword"] for row in caution_rows]
    conn.execute("DELETE FROM caution_keyword WHERE keyword <> ALL(%s)", (caution_keywords,))

    count = conn.execute("SELECT count(*) FROM caution_keyword").fetchone()[0]
    print("넣은 뒤 caution_keyword 행 수:", count)
