import configparser
import boto3
from botocore.exceptions import ClientError

class IntegrationConfigClass:
    """
    Used to get all the required args from AWS secrets manager
    """
    def __init__(self):
        self._config = None
    @property
    def config(self):
        self._config = configparser.ConfigParser()
        config_str = self.get_secret
        self._config.read_string(config_str)
        return self._config
    @property
    def get_secret(self) -> str:
        # Insert the Secret Name of your config file from the AWS secrets manager
        secret_name = "config.ini"
        region_name = "us-east-1"
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e
        # Decrypts secret using the associated KMS key.
        secret = get_secret_value_response['SecretString']
        return secret
