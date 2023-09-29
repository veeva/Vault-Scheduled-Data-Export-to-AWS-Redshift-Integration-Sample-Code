from integrationConfigClass import IntegrationConfigClass
from ingest_deletes import ingest_deletes
from ingest_updates import ingest_updates
from redshift_check_table_details import conn_redshift_alter_create_table
from vault_generate_session_get_objectfields import get_object_fields, get_session_id
from redshift_setup import load_full_data
from sql_str_generation import create_sql_str
from log_message import log_message

settings = IntegrationConfigClass()
# Get the Redshift configuration values
host = settings.config.get('redshift', 'host')
redshift_dbname = settings.config.get('redshift', 'dbname')
aws_username = settings.config.get('redshift', 'user')
aws_password = settings.config.get('redshift', 'password')
port = settings.config.get('redshift', 'port')
redshift_schema = settings.config.get('redshift', 'schema')
bucket_name = settings.config.get('s3', 'bucket_name')
vault_username = settings.config.get('vault', 'username')
vault_password = settings.config.get('vault', 'password')
def process_s3_file(key):
    # Get session id using get_session_id function
    vault_session_id = get_session_id(vault_username, vault_password)
    failed_population = list()
    # Loop through all the objects in the specified folder
    try:
        if key.endswith('.csv'):
            # Split the S3 key based on "/"
            key_parts = key.split("/")
            # The folder name includes all parts except the last one (the file name)
            folder_name = '/'.join(key_parts[:-1])
            # The file name is the last part of the key
            file_name = key_parts[-1]
            # Extract the object name from the file name
            object_name = file_name.split(f'_{settings.config.get("system", "year")}-')[0].split('_', 2)[2]
            log_message(log_level='Info',
                        message=f'Folder - {folder_name}',
                        exception=None, context=None)
            log_message(log_level='Info',
                        message=f'Filename - {file_name}',
                        exception=None, context=None)
            log_message(log_level='Info',
                        message=f'Object Name - {object_name} ',
                        exception=None, context=None)
            # Get the dictionary of fields and types using get_object_fields function
            fields_dict = get_object_fields(object_name, vault_session_id)
            # If a dictionary is empty, bool() will return False, otherwise, it will return True.
            if bool(fields_dict):
                # Perform data operations on the dictionary & make it sql syntax compatible.
                formatted_str = create_sql_str(fields_dict=fields_dict)
                log_message(log_level='Info',
                            message=f'Object Name:{object_name}\nFormatted String: [{formatted_str}]',
                            exception=None, context=None)
                try:
                    # Checks the formatted str with actual table definition.
                    # redshift table already exists - If more columns detected, uses alter table to insert new columns to table definition
                    # else creates table.
                    conn_redshift_alter_create_table(redshift_dbname=redshift_dbname,
                                                     redshift_schema=redshift_schema,
                                                     table_name=object_name,
                                                     formatted_str=formatted_str)
                except Exception as e:
                    log_message(log_level='Error',
                                message=f'',
                                exception=e,
                                context=None)
                # if _updates, _deletes found -
                if file_name.lower().endswith("_deletes.csv"):
                    flag = ingest_deletes(table_name=object_name,
                                          s3_bucket=settings.config.get('s3', 'bucket_name'),
                                          s3_key=folder_name)

                elif file_name.lower().endswith("_updates.csv"):
                    flag = ingest_updates(table_name=object_name,
                                          s3_bucket=settings.config.get('s3', 'bucket_name'),
                                          s3_key=folder_name,
                                          formatted_str=formatted_str)
                else:
                    # Load data in the redshift table - Full files i.e. no UPDATE syntax
                    flag = load_full_data(table_name=object_name,
                                          s3_bucket=settings.config.get('s3', 'bucket_name'),
                                          s3_key=folder_name)
                if flag:
                    log_message(log_level='Debug',
                                message=f'{object_name} is updated with {file_name}',
                                exception=None,
                                context=None)
                    return flag
                else:
                    failed_population.append(object_name)
                    return flag
            else:
                log_message(log_level='Debug',
                            message=f'Vault API request returned with no details - {settings.config.get("vault", "dns")} /api/ {settings.config.get("vault", "version")} /metadata/vobjects/ {object_name}")',
                            exception=None,
                            context=None)
                return False
        log_message(log_level='Debug',
                    message=f'Failed to Populate - {failed_population}',
                    exception=None,
                    context=None)
    except Exception as e:
        log_message(log_level='Error',
                    message=f'',
                    exception=e,
                    context=None)
        return False
