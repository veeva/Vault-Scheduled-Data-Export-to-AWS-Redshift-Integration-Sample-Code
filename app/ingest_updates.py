import psycopg2
import psycopg2.errors
from redshift_setup import get_s3_path
from integrationConfigClass import IntegrationConfigClass
from log_message import log_message

settings = IntegrationConfigClass()
schema = settings.config.get('redshift', 'schema')
redshift_dbname = settings.config.get('redshift', 'dbname')
def ingest_updates(table_name, s3_bucket, s3_key, formatted_str):
    # establish connection
    conn = psycopg2.connect(
        dbname=settings.config.get('redshift', 'dbname'),
        host=settings.config.get('redshift', 'host'),
        port=settings.config.get('redshift', 'port'),
        user=settings.config.get('redshift', 'user'),
        password=settings.config.get('redshift', 'password')
    )
    # Create a cursor
    cur = conn.cursor()
    # Set the S3 path for the updates file
    s3_uri = get_s3_path(tablename=table_name, s3_bucket=s3_bucket, subfolder=s3_key, file_type='updates')
    # Create new temp table with columns from formatted_str
    create_query = f"CREATE TABLE temp_{table_name}_updates ({formatted_str})"
    # Define the COPY command for updates
    copy_updates_query = f"""
    COPY temp_{table_name}_updates FROM '{s3_uri}' 
    IAM_ROLE '{settings.config.get('redshift', 'iam_redshift_s3_read')}' 
    FORMAT AS CSV
    QUOTE '\"' 
    DELIMITER ',' 
    IGNOREHEADER 1
    TIMEFORMAT 'auto'
    """
    cur.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table_name}'")
    table_columns = set(col[0].strip('"') for col in cur.fetchall())
    update_cols_str = ", ".join([f'"{col}" = temp."{col}"' for col in table_columns])
    # Update existing records in the target table
    update_command = f"""
        UPDATE {redshift_dbname}.{schema}.{table_name} 
        SET {update_cols_str}
        FROM temp_{table_name}_updates temp 
        WHERE {redshift_dbname}.{schema}.{table_name}.id = temp.id;"""
    table_columns_str = ', '.join(f'"{col}"' for col in table_columns)
    # Insert new records into the target table
    insert_command = f"""
        INSERT INTO {redshift_dbname}.{schema}.{table_name} ({table_columns_str}) 
        SELECT {table_columns_str} 
        FROM temp_{table_name}_updates 
        WHERE id NOT IN (SELECT id FROM {redshift_dbname}.{schema}.{table_name});"""
    # Drop the temporary table
    drop_command = f"""DROP TABLE IF EXISTS temp_{table_name}_updates"""
    # Execute the commands
    try:
        try:
            cur.execute(create_query)
        except psycopg2.errors.DuplicateTable as e:
            cur.execute(drop_command)
            cur.execute(create_query)
        cur.execute(copy_updates_query)
        cur.execute(update_command)
        cur.execute(insert_command)
        cur.execute(drop_command)
        # Commit the changes
        conn.commit()
        return_flag = True
    except Exception as e:
        log_message(log_level='Error',
                    message=f'',
                    exception=e,
                    context=None)
        conn.rollback()
        return_flag = False
    finally:
        # close the cursor and connection
        cur.close()
        conn.close()
        return return_flag
