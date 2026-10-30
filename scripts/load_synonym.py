import csv
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

with open("data/dict/synonym.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(len(rows), "줄 읽음")

conninfo = (
    f"host={os.getenv('DB_HOST')} port={os.getenv('DB_PORT')} "
    f"dbname={os.getenv('DB_NAME')} user={os.getenv('DB_USER')} password={os.getenv('DB_PASS')}"
)

with psycopg.connect(conninfo) as conn:
    # 사전을 통째로 비우고 CSV대로 다시 넣어요 → 여러 번 실행해도 CSV와 DB가 같아요
    conn.execute("DELETE FROM synonym")
    for row in rows:
        conn.execute(
            "INSERT INTO synonym (word, standard, syn_type) VALUES (%s, %s, %s)",
            (row["word"], row["standard"], row["syn_type"]),
        )

    count = conn.execute("SELECT count(*) from synonym").fetchone()[0]
    print("넣은 뒤 synonym 행 수:", count)