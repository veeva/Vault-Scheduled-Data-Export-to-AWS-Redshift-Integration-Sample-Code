import psycopg2
from redshift_setup import get_s3_path
from integrationConfigClass import IntegrationConfigClass
from log_message import log_message

settings = IntegrationConfigClass()
schema = settings.config.get('redshift', 'schema')
redshift_dbname = settings.config.get('redshift', 'dbname')
def ingest_deletes(table_name, s3_bucket, s3_key):
    # establish connection
    conn = psycopg2.connect(
        dbname=settings.config.get('redshift', 'dbname'),
        host=settings.config.get('redshift', 'host'),
        port=settings.config.get('redshift', 'port'),
        user=settings.config.get('redshift', 'user'),
        password=settings.config.get('redshift', 'password')
    )
    # create a cursor object
    cur = conn.cursor()
    s3_uri = get_s3_path(tablename=table_name, s3_bucket=s3_bucket, subfolder=s3_key, file_type='deletes')
    try:
        # create a temporary table to hold the data from the delete file
        create_query = f"CREATE TEMPORARY TABLE temp_{table_name}_deletes (id VARCHAR, date_deleted TIMESTAMPTZ)"
        log_message(log_level='Info',
                    message=f'create_query: {create_query}',
                    exception=None,
                    context=None)
        cur.execute(create_query)
        # load the data from the _deletes.csv file into the temporary table
        copy_query = f"""
        COPY temp_{table_name}_deletes FROM '{s3_uri}'
        IAM_ROLE '{settings.config.get('redshift', 'iam_redshift_s3_read')}'
        FORMAT AS CSV 
        QUOTE '\"'
        IGNOREHEADER 1
        TIMEFORMAT 'auto'
        """
        log_message(log_level='Info',
                    message=f'copy_query: {copy_query}',
                    exception=None,
                    context=None)
        cur.execute(copy_query)
        # delete the matching rows from the target table
        delete_query = f"DELETE FROM {redshift_dbname}.{schema}.{table_name} WHERE id IN (SELECT id FROM temp_{table_name}_deletes);"
        try:
            log_message(log_level='Info',
                        message=f'delete_query: {delete_query}',
                        exception=None,
                        context=None)
            cur.execute(delete_query)
        except Exception as e:
            log_message(log_level='Error',
                        message=f'',
                        exception=e,
                        context=None)
        # commit the changes
        conn.commit()
        # drop the temp table
        cur.execute(f"DROP TABLE IF EXISTS temp_{table_name}_deletes")
        # commit the changes
        conn.commit()
        log_message(log_level='Info',
                    message=f'Deleted rows from {table_name} where id matched',
                    exception=None,
                    context=None)
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
