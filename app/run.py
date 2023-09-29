import sys
import boto3
import json
from integrationConfigClass import IntegrationConfigClass
from process_inbound_files_no_local import process_s3_file
from log_message import log_message
class AwsSupportClass:
    def __init__(self):
        self._sqs = None
        self._resource = None
    def receive_sqs_messages(self, queue_url, max_number_of_messages, visibility_timeout=30):
        self._sqs = boto3.client(service_name='sqs', region_name='us-east-1')
        # Receive messages from the queue
        response = self._sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_number_of_messages,
            VisibilityTimeout=visibility_timeout
        )
        # Retrieve the received messages
        messages = response.get('Messages', [])
        # Return the received messages
        return messages
    def delete_sqs_messages(self, QueueUrl, ReceiptHandle):
        self._sqs = boto3.client(service_name='sqs', region_name='us-east-1')
        try:
            self._sqs.delete_message(QueueUrl=QueueUrl, ReceiptHandle=ReceiptHandle)
            return True
        except Exception as e:
            log_message(log_level='Error', message='', exception=e, context=None)
            return False
    def send_sqs_message(self, queue_name, file_name, error_msg=None) -> None:
        """
        Function prepares sqs message and sends it to the queue = queue_name
        :param error_msg:
        :param queue_name:
        :param file_name:
        :return:
        """
        try:
            self._sqs = boto3.client(service_name='sqs', region_name='us-east-1')
            queue_url = self._sqs.get_queue_url(QueueName=queue_name)
            error = error_msg if error_msg is not None else "No error message available"
            sqs_msg = {
                "file_name": file_name,
                 "error_message": str(error)
            }
            response = self._sqs.send_message(QueueUrl=queue_url['QueueUrl'], MessageBody=json.dumps(sqs_msg))
            log_message(log_level='Debug',
                        message=f'Successfully added queue message for {file_name} to SQS. Message ID: {response["MessageId"]}',
                        exception=None, context=None)

        except Exception as e:
            log_message(log_level='Error',
                        message=f'Unable to add {file_name} to SQS dlq',
                        exception=e, context=None)
def handler(event, context):
    settings = IntegrationConfigClass()
    queue_url = settings.config.get('sqs', 'input_queue')
    max_number_of_messages = settings.config.get('sqs', 'max_number_of_messages')
    visibility_timeout = settings.config.get('sqs', 'visibility_timeout')
    aws_sqs = AwsSupportClass()
    received_messages = aws_sqs.receive_sqs_messages(queue_url, int(max_number_of_messages), int(visibility_timeout))
    log_message(log_level='Debug',
                message=f'No. of messages received - {len(received_messages)}',
                exception=None,
                context=None)
    # Process the received messages
    for message in received_messages:
        # Access message attributes and body
        message_body = json.loads(json.loads(message['Body'])['Message'])
        s3_file_key = message_body['Records'][0]['s3']['object']['key']
        log_message(log_level='Info',
                    message=f'Message body - {message_body}',
                    exception=None,
                    context=None)
        log_message(log_level='Info',
                    message=f'Found s3_file_key - {s3_file_key}',
                    exception=None,
                    context=None)
        flag = process_s3_file(key=s3_file_key)
        if flag:
            log_message(log_level='Debug',
                        message=f'Success - {s3_file_key}',
                        exception=None,
                        context=None)
        else:
            # Send to DLQ
            log_message(log_level='Debug',
                        message=f'Error while processing - {s3_file_key}',
                        exception=None,
                        context=None)
            log_message(log_level='Debug',
                        message=f'Sending the campaign file to error queue',
                        exception=None,
                        context=None)
            aws_sqs.send_sqs_message(queue_name=settings.config.get('sqs', 'error_queue'), file_name=s3_file_key)
        log_message(log_level='Info',
                    message=f'Deleting the message from the input queue',
                    exception=None, context=None)

        flag = aws_sqs.delete_sqs_messages(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )
        log_message(log_level='Info',
                    message=f'Deleted {message["MessageId"]} from the input queue',
                    exception=None, context=None)
        log_message(log_level='Info',
                    message=f'Exiting For Loop',
                    exception=None, context=None)
    log_message(log_level='Info',
                message=f'Process finished',
                exception=None, context=None)
    return 'Fin. AWS Lambda using Python' + sys.version + '!'


if __name__ == '__main__':
    handler('','')