import requests

BASE_URL = "http://localhost:5000"  # Замените на URL вашего сервера

def get_chats():
    """Получить список всех чатов."""
    url = f"{BASE_URL}/"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def create_chat():
    url = f"{BASE_URL}/create_chat"
    response = requests.post(url)
    response.raise_for_status()
    return response.json()

def get_chat(chat_id, admin_key=None):
    url = f"{BASE_URL}/chat/{chat_id}"
    params = {"admin_key": admin_key} if admin_key else {}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def update_chat_name(chat_id, chat_name):
    url = f"{BASE_URL}/chat/{chat_id}/update_name"
    data = {"chatName": chat_name}
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()

def update_settings(chat_id, settings):
    url = f"{BASE_URL}/chat/{chat_id}/settings"
    response = requests.post(url, json=settings)
    response.raise_for_status()
    return response.json()

def ask_question(chat_id, question):
    url = f"{BASE_URL}/chat/{chat_id}/ask"
    data = {"question": question}
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()

def upload_file(chat_id, file_path=None, url=None):
    url_endpoint = f"{BASE_URL}/chat/{chat_id}/upload"
    if file_path:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post(url_endpoint, files=files)
    elif url:
        data = {'url': url}
        response = requests.post(url_endpoint, data=data)
    else:
        raise ValueError("Необходимо указать file_path или url")

    response.raise_for_status()
    return response.json()

def check_admin_key(chat_id, admin_key):
    url = f"{BASE_URL}/chat/{chat_id}/check_admin_key"
    data = {"admin_key": admin_key}
    response = requests.post(url, json=data)
    response.raise_for_status()
    return response.json()
