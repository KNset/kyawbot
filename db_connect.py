import psycopg2


def get_connection():
    try:
        conn = psycopg2.connect(
            dbname="bot_data",
            user="postgres",
            password="1001",  
            host="72.60.107.248",
            port="5432"
        )
        #conn = psycopg2.connect('postgres://koyeb-adm:npg_P79ROmhtSYdi@ep-misty-sunset-a1xbkiwi.ap-southeast-1.pg.koyeb.app/koyebdb')
        #conn = psycopg2.connect('postgresql://postgres:y7db844eUVmTO4yw@db.xdeewemctoqpcjlrdnkk.supabase.co:5432/postgres')
        #conn = psycopg2.connect('postgresql://neondb_owner:npg_6yIbgvCF0JNe@ep-icy-cell-a4sy2fdi-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require')
        print("Got Connection")
        return conn
    except Exception as e:
        print(e)
        print("Database Connection Error")


get_connection()
