import psycopg2
class RedshiftConnection:
    def __init__(self, db_name, hostname, port_number, username, user_password):
        self.db_name = db_name
        self.host = hostname
        self.port = port_number
        self.user = username
        self.password = user_password
    def run_query(self, query):
        con = psycopg2.connect(dbname=self.db_name, host=self.host, port=self.port,
                               user=self.user, password=self.password)
        cursor = con.cursor()
        cursor.execute(query)
        con.commit()
        cursor.close()
        con.close()
