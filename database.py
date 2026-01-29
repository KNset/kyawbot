import psycopg2
import os


from db_connect import get_connection

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authorized_users (
            username TEXT PRIMARY KEY,
            telegram_id BIGINT,
            smilecoin_balance_br REAL DEFAULT 0,
            smilecoin_balance_ph REAL DEFAULT 0,
            owner_id TEXT 
        );
    ''')
    conn.commit()
    conn.close()

def create_order_br():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS br_order_history (
            id SERIAL PRIMARY KEY,
            username TEXT,
            tele_name TEXT,
            user_id TEXT,
            zone_id TEXT,
            diamond_count TEXT,
            total_cost REAL,
            count TEXT,
            order_ids TEXT,
            time TEXT,
            current_balance REAL
        )
    ''')
    conn.commit()
    conn.close()

def create_order_ph():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ph_order_history (
            id SERIAL PRIMARY KEY,
            username TEXT,
            tele_name TEXT,
            user_id TEXT,
            zone_id TEXT,
            diamond_count TEXT,
            total_cost REAL,
            count TEXT,
            order_ids TEXT,
            time TEXT,
            current_balance REAL
        )
    ''')
    conn.commit()
    conn.close()

def create_admin():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            admin_id TEXT,
            br_coin REAL,
            ph_coin REAL
        )
    ''')
    cursor.execute("INSERT INTO admins (username) VALUES (%s) ON CONFLICT DO NOTHING", ("Drk_RT",))
    conn.commit()
    conn.close()

def is_authorized(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM authorized_users WHERE LOWER(username) = LOWER(%s)", (username,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_user(username, adminid):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO authorized_users (username, owner_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (username,adminid))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def list_users(adid):
    conn = get_connection()
    cursor = conn.cursor()
    ownerid = str(adid)
    if ownerid == '1278018722' or ownerid == '1978808516':
        cursor.execute("SELECT username FROM authorized_users ")
    else:
        cursor.execute("SELECT username FROM authorized_users WHERE owner_id = %s", (ownerid,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def list_admin_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username,br_coin,ph_coin FROM admins ")
    users = cursor.fetchall()
    conn.close()
    return users

def list_admin_id(username):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT admin_id FROM admins WHERE LOWER(username) = LOWER(%s)", (username,))
        ids = [row[0] for row in cursor.fetchall()]
        if ids:
            return True
        else:
            return False
    except Exception as e:
        return False
    finally:
        if conn:
            conn.close()


def remove_user(username, adminid):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        adminid = str(adminid)  # ensure string type for text column

        if adminid in ('1278018722', '1978808516'):
            cursor.execute(
                "DELETE FROM authorized_users WHERE username = %s",
                (username,)
            )
        else:
            cursor.execute(
                "DELETE FROM authorized_users WHERE username = %s AND owner_id = %s",
                (username, adminid)
            )
        
        conn.commit()
        
        # Check how many rows were actually deleted
        if cursor.rowcount > 0:
            return True
        else:
            return False

    except Exception as e:
        print(f"Error removing user: {e}")
        return False

    finally:
        conn.close()






