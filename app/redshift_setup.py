from integrationConfigClass import IntegrationConfigClass
import os
import boto3
from aws_utilities import RedshiftConnection
from log_message import log_message

settings = IntegrationConfigClass()

# Get the Redshift configuration values
host = settings.config.get('redshift', 'host')
dbname = settings.config.get('redshift', 'dbname')
user = settings.config.get('redshift', 'user')
password = settings.config.get('redshift', 'password')
port = settings.config.get('redshift', 'port')
schema = settings.config.get('redshift', 'schema')
year = settings.config.get('system', 'year')

# Create a Redshift connection
redshift_conn = RedshiftConnection(
    db_name=dbname,
    hostname=host,
    port_number=port,
    username=user,
    user_password=password
)
def redshift_table_exists(table_catalog: str, table_schema:str, table_name: str) -> bool:
    query = f"""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE
            table_catalog = '{table_catalog}' 
            AND table_schema = '{table_schema}'
            AND table_name = '{table_name}'
        )
    """
    try:
        result = redshift_conn.run_query(query)
        return result.iloc[0][0]
    except Exception as e:
        log_message(log_level='Error',
                    message=f'Error checking if table {table_catalog}.{table_schema}.{table_name} exists',
                    exception=e,
                    context=None)
        return False
def redshift_update_table(table_catalog: str, table_schema:str, table_name: str, formatted_query: str) -> bool:
    query = f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE
        table_catalog = '{table_catalog}' 
        AND table_schema = '{table_schema}'
        AND table_name = '{table_name}'
    """
    redshift_table_name = f"{table_schema}.{table_name}"
    try:
        current_columns = set(redshift_conn.run_query(query)['column_name'])
        new_columns = set([col.split()[0] for col in formatted_query.split(',')])
        if current_columns == new_columns:
            return True
        else:
            columns_to_add = ', '.join(new_columns - current_columns)
            redshift_table_name = f"{table_schema}.{table_name}"
            redshift_alter_table(table_catalog, redshift_table_name, f"ADD COLUMN {columns_to_add}")
            return True
    except Exception as e:
        log_message(log_level='Error',
                    message=f'Error updating table {redshift_table_name}',
                    exception=e,
                    context=None)
        return False
def read_s3_bucket(s3_bucket, folder_name):
    """
    Function to read the S3 bucket and list the names of files in a folder named as today's date.
    """
    s3_client = boto3.client('s3')
    # use delimiter to list only keys present at the root level
    response = s3_client.list_objects_v2(Bucket=s3_bucket)
    keys = []
    for obj in response['Contents']:
        if f'{folder_name}_' in obj['Key']:
            keys.append(obj['Key'])
    return keys
def extract_object_name(filename):
    """
    Function to extract the object name from the file name.
    """
    object_name = filename.split(f'_{year}-')[0].split('_', 2)[2]
    return object_name
def write_schemas_to_files(table_schemas, schema_path):
    # create the schema directory if it doesn't exist
    if not os.path.exists(schema_path):
        os.makedirs(schema_path)

    # iterate through each table and write its schema to a file
    for table_name, schema in table_schemas.items():
        file_path = os.path.join(schema_path, f"{table_name}.csv")
        with open(file_path, 'w') as f:
            f.write(schema)
def redshift_alter_table(redshift_dbname, redshift_table_name, formatted_query):
    if ',' not in formatted_query:
        formatted_query = formatted_query.strip()
        return _run_alter_query(redshift_dbname, redshift_table_name, formatted_query)
    else:
        columns = formatted_query.split(',')
        for column in columns:
            column = column.strip()
            if column:
                _run_alter_query(redshift_dbname, redshift_table_name, column)
def _run_alter_query(redshift_dbname, redshift_table_name, column):
    query = f"ALTER TABLE {redshift_dbname}.{redshift_table_name} {column};"
    try:
        redshift_conn.run_query(query)
        return True
    except Exception as e:
        log_message(log_level='Error',
                    message=f'Error in altering table {redshift_table_name}',
                    exception=e,
                    context=None)
        return False
def get_s3_path(tablename, s3_bucket, subfolder, file_type):
    """

    :param tablename:
    :param s3_bucket:
    :param subfolder:
    :param file_type: full, updates or deletes. Depending on these choices, the file key is searched.
    :return:
    """
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(s3_bucket)
    prefix = f"{subfolder}/"
    for obj in bucket.objects.filter(Prefix=prefix):
        if tablename in obj.key and obj.key.endswith(f'_{file_type}.csv'):
            return f"s3://{s3_bucket}/{obj.key}"
    log_message(log_level='Info',
                message=f'For {tablename}, s3 file not found',
                exception=None, context=None)
    return None
def load_full_data(table_name, s3_bucket, s3_key):
    """
    # Function to load data into Redshift
    """
    s3_uri = get_s3_path(tablename=table_name, s3_bucket=s3_bucket, subfolder=s3_key, file_type='full')
    if not s3_uri is None:
        redshift_dbname = dbname
        query = f"COPY {redshift_dbname}.{schema}.{table_name} FROM '{s3_uri}' " \
                f"IAM_ROLE '{settings.config.get('redshift', 'iam_redshift_s3_read')}' " \
                f"FORMAT AS CSV " \
                f"QUOTE '\"' " \
                f"IGNOREHEADER 1 " \
                f"TIMEFORMAT 'auto'" \
                f"ACCEPTINVCHARS " \
                f"FILLRECORD"
        try:
            redshift_conn.run_query(query)
            log_message(log_level='Debug',
                        message=f'{table_name} populated',
                        exception=None,
                        context=None)
            return True
        except Exception as e:
            log_message(log_level='Error',
                        message=f'{table_name}',
                        exception=e, context=None)
            return False
    else:
        log_message(log_level='Info',
                    message=f'Load operation for {table_name} is skipped',
                    exception=None, context=None)
        return True
