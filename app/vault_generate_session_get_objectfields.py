import requests
from integrationConfigClass import IntegrationConfigClass
from log_message import log_message

settings = IntegrationConfigClass()
def get_object_fields(object_name, session_id):
    url = f"{settings.config.get('vault', 'dns')}/api/{settings.config.get('vault', 'version')}/metadata/vobjects/{object_name}"
    headers = {
        'Authorization': session_id,
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    if data['responseStatus'] == 'SUCCESS':
        fields = data.get('object', {}).get('fields', [])
        return {field['name']: field['type'] for field in fields}
    else:
        log_message(log_level='Error',
                    message=f'Failed to get fields for {object_name} Status code: {response.status_code}',
                    exception=None,
                    context=data['responseStatus'])
        return {}
def get_session_id(username, password):
    url = f"{settings.config.get('vault', 'dns')}/api/{settings.config.get('vault', 'version')}/auth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    data = {
        'username': username,
        'password': password
    }
    response = requests.post(url, headers=headers, data=data)
    response_json = response.json()
    session_id = response_json['sessionId']
    return session_id
def get_object_metadata(session_id, object_name):
    url = f"{settings.config.get('vault', 'dns')}/api/{settings.config.get('vault', 'version')}/metadata/vobjects/{object_name}"
    headers = {
        'Authorization': session_id,
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    response_json = response.json()
    return response_json
