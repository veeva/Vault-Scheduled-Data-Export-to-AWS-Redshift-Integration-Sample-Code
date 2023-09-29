from integrationConfigClass import IntegrationConfigClass
import psycopg2
from log_message import log_message

settings = IntegrationConfigClass()
def conn_redshift_alter_create_table(redshift_dbname, redshift_schema, table_name, formatted_str):
    conn = psycopg2.connect(
        dbname=settings.config.get('redshift', 'dbname'),
        host=settings.config.get('redshift', 'host'),
        port=settings.config.get('redshift', 'port'),
        user=settings.config.get('redshift', 'user'),
        password=settings.config.get('redshift', 'password')
    )
    cur = conn.cursor()
    # Check if table exists
    cur.execute(
        f"SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_schema = '{redshift_schema}' AND table_name = '{table_name}')")
    table_exists = cur.fetchone()[0]
    if table_exists:
        # Check if table columns match with formatted_str
        cur.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{redshift_schema}' AND table_name = '{table_name}'")
        table_columns = set(col[0].strip('"') for col in cur.fetchall())
        new_columns = set(col.split()[0].strip('"') for col in formatted_str.split(','))
        if table_columns != new_columns:
            # Add new columns to the table
            additional_columns = new_columns - table_columns
            log_message(log_level='Debug',
                        message=f'{table_name} has additional columns - {additional_columns}',
                        exception=None,
                        context=None)
            for col in additional_columns:
                try:
                    cur.execute(f'ALTER TABLE {redshift_schema}.{table_name} ADD COLUMN "{col}" VARCHAR (255)')
                    log_message(log_level='Info',
                                message=f'Added column "{col}" to table "{table_name}"',
                                exception=None,
                                context=None)
                except Exception as e:
                    log_message(log_level='Error',
                                message=f'',
                                exception=e,
                                context=None)
    else:
        # Create new table with columns from formatted_str
        create_query = f"CREATE TABLE {redshift_schema}.{table_name} ({formatted_str})"
        cur.execute(create_query)
        log_message(log_level='Info',
                    message=f'Created redshift table "{table_name}"',
                    exception=None,
                    context=None)
    conn.commit()
    cur.close()
    conn.close()
