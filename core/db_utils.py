import sqlite3
import datetime

FILENAME = "storage.sqlite"


def create_db():
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()

    cursor.execute("""
            CREATE TABLE "jobs" (
            "id"	                INTEGER PRIMARY KEY AUTOINCREMENT,
            "name"	                TEXT,
            "started"	            DATETIME,
            "completed"	            DATETIME
	        
        );
    """)

    sqlite_connection.commit()
    cursor.close()


def new_job(job_name):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    cursor.execute(
        """INSERT INTO 
        jobs
        (name,started) VALUES (?,?)""",
        (job_name, now),
    )
    job_id = cursor.lastrowid
    cursor.execute(f"""
        CREATE TABLE "{job_name}_{job_id}" (
            "goods_id"              TEXT,
            "merchant_id"           TEXT,
            "url"	                TEXT,
            "title"                 TEXT,
            "price"	                INTEGER,
            "price_bonus"           INTEGER,
            "bonus_amount"	        INTEGER,
            "bonus_percent"	        INTEGER,
            "available_quantity"    INTEGER,
            "delivery_date"         TEXT,
            "merchant_name"         TEXT,
            "merchant_rating"       FLOAT,
            "scraped_at"	        DATETIME,
            "notified"              BOOL
        );
    """)
    sqlite_connection.commit()
    return job_id


def add_to_db(
    job_id,
    job_name,
    goods_id,
    merchant_id,
    url,
    title,
    price,
    price_bonus,
    bonus_amount,
    bonus_percent,
    available_quantity,
    delivery_date,
    merchant_name,
    merchant_rating,
    notified,
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    cursor.execute(
        f"""INSERT INTO 
        "{job_name}_{job_id}"
        (goods_id,merchant_id,url,title,price,price_bonus,bonus_amount,
        bonus_percent,available_quantity,delivery_date,
        merchant_name,merchant_rating,scraped_at,notified)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            goods_id,
            merchant_id,
            url,
            title,
            price,
            price_bonus,
            bonus_amount,
            bonus_percent,
            available_quantity,
            delivery_date,
            merchant_name,
            merchant_rating,
            now,
            notified,
        ),
    )
    sqlite_connection.commit()


def get_last_notified(goods_id, merchant_id, price, bonus_amount):
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    last_notified_row = None

    # Get a list of all job tables
    # cursor.execute("SELECT id, name FROM jobs")
    # job_tables = cursor.fetchall()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'jobs' AND name != 'sqlite_sequence'")
    job_tables = [table[0] for table in cursor.fetchall()]

    # Construct a union query to select from all job tables at once
    union_query = " UNION ".join([f"SELECT scraped FROM '{table}' WHERE notified = 1 AND goods_id = ? AND merchant_id = ? AND price = ? AND bonus_amount = ?" for table in job_tables])

    union_query += "ORDER BY scraped DESC LIMIT 1"

    # Concatenate all parameters to be passed into the execute function
    parameters = tuple([goods_id, merchant_id, price, bonus_amount] * len(job_tables))

    cursor.execute(union_query, parameters)
    row = cursor.fetchone()
    if row:
        last_notified_row = row[0]

    cursor.close()
    return last_notified_row


def finish_job(job_id):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    cursor.execute(
        """UPDATE
        "jobs"
        SET completed = ?
        WHERE id = ?
        """,
        (now, job_id),
    )
    sqlite_connection.commit()
    cursor.close()
    if cursor.rowcount == 0:
        return False
    return True
