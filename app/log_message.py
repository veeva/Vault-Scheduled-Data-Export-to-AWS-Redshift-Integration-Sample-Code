import datetime
import traceback
def log_message(log_level, message, exception=None, context=None):
    """
    Logs a message with the specified log level.

    Parameters:
        log_level (str): The severity level of the log message.
        Valid values include 'Info', 'Debug', 'Error', and others.

        message (str): The log message to be logged.
        exception (Exception, optional): An exception object to log the exception details and traceback. Defaults to None.
        context (str, optional): Additional contextual information. Defaults to None.

    # Example usage
try:
    # Code that may raise an exception
    raise ValueError("Something went wrong")
except ValueError as ex:
    log_message("Error", "An error occurred", exception=ex, context="Additional context")
    :return:
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{log_level}] {timestamp} - {message}"
    if exception:
        log_entry += f"\nException: {exception}\n{traceback.format_exc()}"
    if context:
        log_entry += f"\nContext: {context}"
    print(log_entry)
