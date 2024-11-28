from flask import Flask, request, render_template, jsonify, redirect, url_for
import json
import os
import uuid
from werkzeug.utils import secure_filename
import docx
from PyPDF2 import PdfReader
import requests
from notion_client import Client as NotionClient
from atlassian import Confluence
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering


app = Flask(__name__)

model_name = "distilbert-base-uncased-distilled-squad"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer, framework="pt")


CHAT_DATA_DIR = "chat_data"
UPLOAD_FOLDER = "uploaded_files"
os.makedirs(CHAT_DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

NOTION_TOKEN = "your_notion_token"  # Замените на ваш Notion API токен
CONFLUENCE_URL = "https://your_confluence_instance_url"  # Замените на ваш URL Confluence
CONFLUENCE_USER = "your_user"  # Замените на вашего пользователя Confluence
CONFLUENCE_PASS = "your_password"  # Замените на ваш пароль Confluence

# Функция для проверки допустимых расширений файлов
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Функция для парсинга PDF
def parse_pdf(file_path):
    content = ""
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        content = "\n".join([page.extract_text() for page in reader.pages])
    return content

# Функция для парсинга DOCX
def parse_docx(file_path):
    content = ""
    doc = docx.Document(file_path)
    content = "\n".join([para.text for para in doc.paragraphs])
    return content

# Функция для загрузки данных из Notion
def fetch_notion_data(page_id):
    notion = NotionClient(auth=NOTION_TOKEN)
    page = notion.pages.retrieve(page_id)
    return page['properties']['title']['title'][0]['text']['content']

# Функция для загрузки данных из Confluence
def fetch_confluence_data(page_id):
    confluence = Confluence(
        url=CONFLUENCE_URL,
        username=CONFLUENCE_USER,
        password=CONFLUENCE_PASS
    )
    page = confluence.get_page_by_id(page_id)
    return page['body']['storage']['value']

# Главная страница со списком чатов
@app.route('/')
def home():
    chats = []
    for f in os.listdir(CHAT_DATA_DIR):
        if f.endswith(".txt"):
            chat_id = f.replace("chat_", "").replace(".txt", "")
            settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f_settings:
                    settings = json.load(f_settings)
                    chats.append({
                        "chat_id": chat_id,
                        "chat_name": settings.get("chat_name", "Без имени"),
                        "logo_url": settings.get("logo_url", "/default-logo.png")
                    })
    return render_template('index.html', chats=chats)

# Создание нового чата
@app.route('/create_chat', methods=['POST'])
def create_chat():
    chat_id = str(uuid.uuid4())
    chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
    open(chat_file, 'w').close()

    # Генерация уникального ключа для доступа к админ панели
    admin_key = str(uuid.uuid4())

    settings = {
        "chat_name": "Новый чат",
        "logo_url": "/default-logo.png",
        "header_color": "#007bff",
        "input_color": "#ffffff",
        "bg_color": "#ffffff",
        "public": True,
        "admin_key": admin_key  # Добавляем ключ администратора
    }

    settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f)

    # Отображаем ключ администратора на новой странице перед перенаправлением
    return render_template('show_admin_key.html', admin_key=admin_key, chat_id=chat_id)


@app.route('/chat/<chat_id>', methods=['GET', 'POST'])
def chat(chat_id):
    # Загрузка данных чата
    chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
    if not os.path.exists(chat_file):
        return "Чат не найден.", 404

    settings = {}  # Инициализируем как пустой словарь

    # Проверка наличия файла настроек и загрузка
    settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

    admin_error = False
    admin_access = False

    # Получаем ключ администратора из GET-запроса
    input_key = request.args.get('admin_key')
    if input_key == settings.get('admin_key'):  # Проверка правильности ключа
        admin_access = True

    # Если POST-запрос с ключом администратора
    if request.method == 'POST':
        input_key = request.form.get('admin_key')
        if input_key == settings.get('admin_key'):  # Проверка правильности ключа
            admin_access = True
        else:
            admin_error = True

    # Загрузка истории чата
    with open(chat_file, 'r', encoding='utf-8') as f:
        raw_history = f.readlines()

    history = []
    for line in raw_history:
        if line.strip():  # Пропускаем пустые строки
            try:
                history.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                print(f"Некорректная строка: {line.strip()}")

    # Передаем переменную settings в шаблон
    return render_template('chat.html', chat_id=chat_id, settings=settings, history=history,
                           admin_error=admin_error, admin_access=admin_access)

# Сохранение названия чата
@app.route('/chat/<chat_id>/update_name', methods=['POST'])
def update_chat_name(chat_id):
    chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
    if not os.path.exists(chat_file):
        return jsonify({"error": "Чат не найден"}), 404

    data = request.json
    chat_name = data.get("chatName")

    settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")
    with open(settings_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    settings['chat_name'] = chat_name

    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f)

    return jsonify({"message": "Название чата обновлено", "chatName": chat_name})

# Обновление настроек
@app.route('/chat/<chat_id>/settings', methods=['POST'])
def update_settings(chat_id):
    app.logger.info(f"Получен запрос на обновление настроек для чата: {chat_id}")
    data = request.json
    app.logger.info(f"Полученные данные: {data}")

    chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
    if not os.path.exists(chat_file):
        return jsonify({"error": "Чат не найден"}), 404

    settings = {
        "header_color": data.get("headerColor", "#007bff"),
        "input_color": data.get("inputColor", "#ffffff"),
        "bg_color": data.get("bgColor", "#ffffff"),
        "logo_url": data.get("logoUrl", "/default-logo.png"),
        "public": data.get("public", True),
        "chat_name": data.get("chatName", "Новый чат")
    }

    settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f)

    return jsonify({"message": "Настройки обновлены"})


@app.route('/chat/<chat_id>/ask', methods=['POST'])
def ask_question(chat_id):
    chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
    if not os.path.exists(chat_file):
        return jsonify({"error": "Чат не найден"}), 404

    data = request.json
    question = data.get("question")
    if not question:
        return jsonify({"error": "Вопрос не задан"}), 400

    # Получение базы знаний из загруженных данных
    knowledge_base = ""
    with open(chat_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        knowledge_base = " ".join(lines)

    if not knowledge_base.strip():
        return jsonify({"error": "База знаний пуста. Загрузите данные для поиска ответа."}), 400

    # Используем модель Hugging Face для ответа
    try:
        answer = qa_pipeline({"question": question, "context": knowledge_base})
        bot_response = answer['answer']
    except Exception as e:
        return jsonify({"error": f"Ошибка при обработке вопроса: {str(e)}"}), 500

    # Сохранение в историю чата
    with open(chat_file, 'a', encoding='utf-8') as f:
        json.dump({"user": question, "bot": bot_response}, f, ensure_ascii=False)
        f.write('\n')

    return jsonify({"answer": bot_response})

# Загрузка файлов
@app.route('/chat/<chat_id>/upload', methods=['POST'])
def upload_file(chat_id):
    if 'file' not in request.files and 'url' not in request.form:
        return jsonify({"error": "Нет файла или URL для загрузки"}), 400

    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Файл не выбран"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # Парсинг содержимого файла
            content = ""
            if filename.endswith('.txt'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif filename.endswith('.pdf'):
                content = parse_pdf(filepath)
            elif filename.endswith('.docx'):
                content = parse_docx(filepath)

            # Добавление контента в чат
            chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
            if os.path.exists(chat_file):
                with open(chat_file, 'a', encoding='utf-8') as f:
                    f.write(f"Загруженный файл:\n{content}\n")

            return jsonify({"message": "Файл успешно загружен и обработан", "content": content}), 200
        else:
            return jsonify({"error": "Неподдерживаемый формат файла"}), 400

    # Обработка URL
    if 'url' in request.form:
        url = request.form['url']
        content = ""

        # Проверка, если это Notion
        if url.startswith("https://www.notion.so/"):
            page_id = url.split("/")[-1]  # Просто пример, вы должны подстроить под вашу логику
            content = fetch_notion_data(page_id)

        # Проверка, если это Confluence
        elif url.startswith("https://your_confluence_instance.atlassian.net/wiki/pages/viewpage.action?pageId="):
            page_id = url.split("=")[-1]  # Также, подстроить под вашу логику
            content = fetch_confluence_data(page_id)

        # Проверка, если это обычный URL
        else:
            try:
                response = requests.get(url)
                content = response.text
            except Exception as e:
                return jsonify({"error": f"Не удалось получить данные с URL: {str(e)}"}), 400

        # Добавление контента в чат
        chat_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}.txt")
        if os.path.exists(chat_file):
            with open(chat_file, 'a', encoding='utf-8') as f:
                f.write(f"Загруженный контент с URL:\n{content}\n")

        return jsonify({"message": "Контент с URL успешно загружен", "content": content}), 200

# Проверка ключа администратора
@app.route('/chat/<chat_id>/check_admin_key', methods=['POST'])
def check_admin_key(chat_id):
    data = request.json
    admin_key = data.get("admin_key")
    settings_file = os.path.join(CHAT_DATA_DIR, f"chat_{chat_id}_settings.json")

    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        if admin_key == settings.get('admin_key'):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False})
    return jsonify({"success": False})

if __name__ == '__main__':
    app.run(debug=True)
