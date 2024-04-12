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
        (job_name,
        now)
    )
    job_id = cursor.lastrowid
    cursor.execute(f"""
        CREATE TABLE "{job_name}_{job_id}" (
            "goodsId"               TEXT,
            "merchantId"            TEXT,
            "url"	                TEXT,
            "title"                 TEXT,
            "finalPrice"	        INTEGER,
            "finalPriceBonus"       INTEGER,
            "bonusAmount"	        INTEGER,
            "bonusPercent"	        INTEGER,
            "availableQuantity"     INTEGER,
            "deliveryPossibilities" TEXT,
            "merchantName"          TEXT,
            "scraped"	            DATETIME,
            "notified"              BOOL
        );
    """)
    sqlite_connection.commit()
    return job_id


def add_to_db(
    job_id,
    job_name,
    goodsId,
    merchantId,
    url,
    title,
    finalPrice,
    finalPriceBonus,
    bonusAmount,
    bonusPercent,
    availableQuantity,
    deliveryPossibilities,
    merchantName,
    notified,
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    cursor.execute(
        f"""INSERT INTO 
        "{job_name}_{job_id}"
        (goodsId,merchantId,url,title,finalPrice,finalPriceBonus,bonusAmount,
        bonusPercent,availableQuantity,deliveryPossibilities,
        merchantName,scraped,notified)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            goodsId,
            merchantId,
            url,
            title,
            finalPrice,
            finalPriceBonus,
            bonusAmount,
            bonusPercent,
            availableQuantity,
            deliveryPossibilities,
            merchantName,
            now,
            notified,
        ),
    )
    sqlite_connection.commit()


def get_last_notified(goodsId, merchantId, finalPrice, bonusAmount):
    sqlite_connection = sqlite3.connect(FILENAME)
    cursor = sqlite_connection.cursor()
    last_notified_row = None

    # Get a list of all job tables
    # cursor.execute("SELECT id, name FROM jobs")
    # job_tables = cursor.fetchall()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'jobs' AND name != 'sqlite_sequence'")
    job_tables = [table[0] for table in cursor.fetchall()]

    # Construct a union query to select from all job tables at once
    union_query = " UNION ".join([f"SELECT scraped FROM {table} WHERE notified = 1 AND goodsId = ? AND merchantId = ? AND finalPrice = ? AND bonusAmount = ?" for table in job_tables])

    union_query+="ORDER BY scraped DESC LIMIT 1"

    # Concatenate all parameters to be passed into the execute function
    parameters = tuple([goodsId, merchantId, finalPrice, bonusAmount] * len(job_tables))

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
