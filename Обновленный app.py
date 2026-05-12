from flask import Flask, request, jsonify
import logging
import random
from datetime import datetime

from config import Config
from models import db, UserProgress

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)

logging.basicConfig(level=logging.INFO)

REBUSES = [
    {"id": 1, "answer": "ангелина", "hint_letter": "а",
     "length": 8, "text": "Разгадайте имя",
     "image_id": "14236656/a28d23c0c73efe1b4013"},
    {"id": 2, "answer": "сосна", "hint_letter": "с",
     "length": 5, "text": "Что здесь зашифровано?",
     "image_id": "965417/17343d432e4c1913d2cb"},
    {"id": 3, "answer": "лиса", "hint_letter": "л",
     "length": 4, "text": "Кто это?",
     "image_id": "965417/bb148c3bfc4ac6d6b482"},
    {"id": 4, "answer": "волк", "hint_letter": "в",
     "length": 4, "text": "Отгадайте зверя",
     "image_id": "1540737/7702ddacd56f9c4cec54"},
    {"id": 5, "answer": "дом", "hint_letter": "д",
     "length": 3, "text": "Где мы живем?",
     "image_id": "965417/3b390ee65413c3d34041"},
    {"id": 6, "answer": "кот", "hint_letter": "к",
     "length": 3, "text": "Домашний зверь",
     "image_id": "1521359/b97bdebf35d9a4c89f6e"},
    {"id": 7, "answer": "мяч", "hint_letter": "м",
     "length": 3, "text": "Игрушка",
     "image_id": "1540737/5e750593cb663009dc74"},
    {"id": 8, "answer": "слон", "hint_letter": "с",
     "length": 4, "text": "Большое животное",
     "image_id": "965417/86d46ae8aed8bfde8e60"},
    {"id": 9, "answer": "мишка", "hint_letter": "м",
     "length": 5, "text": "Лесной житель",
     "image_id": "1540737/6a9cc3d6e20c1395680e"},
    {"id": 10, "answer": "заяц", "hint_letter": "з",
     "length": 4, "text": "Длинноухий зверь",
     "image_id": "965417/9c808ba7bd3a6382620f"},
    {"id": 11, "answer": "рыба", "hint_letter": "р",
     "length": 4, "text": "Живет в воде",
     "image_id": "1540737/c952eaf0964bf678d140"},
    {"id": 12, "answer": "птица", "hint_letter": "п",
     "length": 5, "text": "Умеет летать",
     "image_id": "1540737/4f6250c1fe3178b29615"},
    {"id": 13, "answer": "маятник", "hint_letter": "м",
     "length": 7, "text": "Сложный ребус",
     "image_id": "1540737/48304cde6020c47eba4e"},
    {"id": 14, "answer": "рыбак", "hint_letter": "р",
     "length": 5, "text": "Человек с удочкой",
     "image_id": "1540737/27a73d01a07b76fffc73"},
    {"id": 15, "answer": "снегирь", "hint_letter": "с",
     "length": 7, "text": "Зимняя птица",
     "image_id": "965417/96c688a72262f19fb641"},
    {"id": 16, "answer": "луноход", "hint_letter": "л",
     "length": 7, "text": "Космический транспорт",
     "image_id": "1652229/8c7c98a537963415656a"},
    {"id": 17, "answer": "паровоз", "hint_letter": "п",
     "length": 7, "text": "Старый поезд",
     "image_id": "14236656/48b676bc8391145155db"},
    {"id": 18, "answer": "корабль", "hint_letter": "к",
     "length": 7, "text": "Плывет по морю",
     "image_id": "965417/761ac00208a3e39cc146"},
    {"id": 19, "answer": "самолет", "hint_letter": "с",
     "length": 7, "text": "Железная птица",
     "image_id": "1540737/a80c8f732fd0821cb56b"},
    {"id": 20, "answer": "бегемот", "hint_letter": "б",
     "length": 7, "text": "Житель Африки",
     "image_id": "1521359/77bdbaf8554e9500ba20"},
]

# Хранилище сессий, которое сохраняет состояние игры для каждого пользователя
# Его ключ - user_id, а значение - словарь с данными игрока
sessionStorage = {}

with app.app_context():
    db.create_all()

def normalize_command(raw_command):
    if not raw_command:
        return ''
    command = raw_command.lower().strip()
    forbidden = ['sql', 'drop', 'delete', 'insert', 'update', 'exec', 'script']
    for word in forbidden:
        if word in command:
            return ''
    return command

def is_valid_command(command):
    if not command or len(command) > 100:
        return False
    return True

def is_skip_command(command):
    skip_keywords = ['пропустить', 'пропусти', 'скип', 'skip', 'пропуск', 'мимо']
    return any(kw in command for kw in skip_keywords)

def is_exit_command(command):
    exit_keywords = ['выход', 'хватит', 'стоп', 'закончить', 'quit', 'exit', 'конец']
    return any(kw in command for kw in exit_keywords)

def is_history_command(command):
    history_keywords = ['все очки', 'история', 'счет', 'очки', 'баллы', 'результат']
    return any(kw in command for kw in history_keywords)

def is_hint_command(command):
    hint_keywords = ['подсказка', 'буква', 'подскажи']
    return any(kw in command for kw in hint_keywords)

def is_next_command(command):
    next_keywords = ['дальше', 'следующий', 'далее', 'след', 'next']
    return any(kw in command for kw in next_keywords)

def is_difficulty_command(command):
    return 'легкий' in command or 'сложный' in command

def calculate_points(used_hint, attempts):
    if used_hint:
        return 0
    if attempts == 0:
        return 2
    elif attempts == 1:
        return 1
    else:
        return 0

def get_random_rebus_from_pool(pool):
    if not pool:
        return None
    return random.choice(pool)

# Функции для формирования ответов и кнопок
def add_difficulty_buttons(res):
    res['response']['buttons'] = [
        {'title': 'Легкий', 'hide': True},
        {'title': 'Сложный', 'hide': True}
    ]

def add_standard_buttons(res):
    res['response']['buttons'] = [
        {'title': 'Подсказка', 'hide': True},
        {'title': 'Все очки', 'hide': True},
        {'title': 'Дальше', 'hide': True},
        {'title': 'Выход', 'hide': True}
    ]

def add_game_over_buttons(res):
    res['response']['buttons'] = [
        {'title': 'Дальше', 'hide': True},
        {'title': 'Все очки', 'hide': True},
        {'title': 'Выход', 'hide': True}
    ]

def add_history_buttons(res):
    res['response']['buttons'] = [
        {'title': 'Подсказка', 'hide': True},
        {'title': 'Все очки', 'hide': True},
        {'title': 'Дальше', 'hide': True},
        {'title': 'Выход', 'hide': True}
    ]

def build_win_text(state, points):
    return f'✅ Правильно!\n+{points} баллов\nТекущий счёт: {state["score"]}\n\nСкажите «дальше»'

def build_fail_text(curr):
    return f'Попытки закончились.\nПравильный ответ: {curr["answer"]}'

def build_skip_text(curr):
    return f'⏭️ Вопрос пропущен. Правильный ответ: {curr["answer"]}\n\nСкажите «дальше» для продолжения'

def build_wrong_text(state):
    return f'Неверно. Осталось попыток: {3 - state["attempts"]}'

def build_history_text(state):
    if not state['history']:
        return 'У вас пока нет очков'
    lines = [f'{i + 1}) {h["answer"]} → +{h["points"]}' for i, h in enumerate(state['history'])]
    return '📊 История:\n' + '\n'.join(lines) + f'\n\nИтого: {state["score"]}'

def prepare_response_template(req):
    return {
        'session': req['session'],
        'version': req['version'],
        'response': {'end_session': False}
    }

def init_new_session(user_id):
    sessionStorage[user_id] = {'mode': 'choose'}

def reset_game_state(state):
    state.update({
        'mode': 'game',
        'score': 0,
        'attempts': 0,
        'used_hint': False,
        'history': []
    })

# Получение данных пользователя, а также их сохранение в базе данных
def get_or_create_user(user_id):
    user = UserProgress.query.filter_by(user_id=user_id).first()
    if not user:
        user = UserProgress(user_id=user_id)
        db.session.add(user)
        db.session.commit()
    return user

# Основной эндпоинт для приёма POST-запросов от Алисы
@app.route('/post', methods=['POST'])
def main():
    # Формируем базовый ответ с сессией и версией протокола
    response = prepare_response_template(request.json)
    # Вызывает функцию обработки диалога
    handle_dialog(response, request.json)
    return jsonify(response)

# Функция диалогового окна
def handle_dialog(res, req):
    user_id = req['session']['user_id']
    raw_command = req['request']['command']
    command = normalize_command(raw_command)
    user = get_or_create_user(user_id)

    if not is_valid_command(raw_command):
        res['response']['text'] = 'Пожалуйста, введите корректную команду.'
        add_standard_buttons(res)
        return

    if req['session']['new']:
        init_new_session(user_id)
        res['response']['text'] = 'Добро пожаловать в «Слово за словом»!\nВыберите сложность:'
        add_difficulty_buttons(res)
        return

    state = sessionStorage.get(user_id)
    if not state:
        init_new_session(user_id)
        state = sessionStorage[user_id]

    # Выбор сложности
    if state['mode'] == 'choose':
        if 'легкий' in command:
            state['pool'] = [r for r in REBUSES if r['length'] <= 5]
            res['response']['text'] = '✅ Выбран Лёгкий уровень (до 5 букв).'
        elif 'сложный' in command:
            state['pool'] = [r for r in REBUSES if r['length'] > 5]
            res['response']['text'] = '✅ Выбран Сложный уровень (более 5 букв).'
        else:
            res['response']['text'] = 'Пожалуйста, выберите «Легкий» или «Сложный».'
            add_difficulty_buttons(res)
            return

        reset_game_state(state)
        state['current'] = get_random_rebus_from_pool(state['pool'])
        show_rebus(res, state)
        return

    curr = state['current']
    if curr is None:
        state['current'] = get_random_rebus_from_pool(state['pool'])
        curr = state['current']

    # Команда пропуска текущего вопроса (без начисления очков, без занесения в историю)
    if is_skip_command(command):
        state['history'].append({'answer': curr['answer'], 'points': 0, 'skipped': True})
        res['response']['text'] = build_skip_text(curr)
        add_game_over_buttons(res)
        return

    # Основные команды
    # Команда завершения ребуса
    if is_exit_command(command):
        save_game_result(user, state)
        res['response']['text'] = f'Игра окончена!\nВаш итоговый счёт: {state["score"]} баллов.'
        res['response']['end_session'] = True
        return

    if is_history_command(command):
        res['response']['text'] = build_history_text(state)
        add_history_buttons(res)
        return

    # Команда получения подсказки
    if is_hint_command(command):
        state['used_hint'] = True
        res['response']['text'] = f'Первая буква: {curr["hint_letter"].upper()}'
        add_standard_buttons(res)
        return

    # Команда перехода на следующий ребус
    if is_next_command(command):
        next_rebus(res, state)
        return

    # Проверка ответа
    if command == curr['answer']:
        points = calculate_points(state['used_hint'], state['attempts'])
        state['score'] += points
        state['history'].append({'answer': curr['answer'], 'points': points})
        res['response']['text'] = build_win_text(state, points)
        add_game_over_buttons(res)
        return

    # Если ответ неправильный ответ
    state['attempts'] += 1
    if state['attempts'] >= 3:
        state['history'].append({'answer': curr['answer'], 'points': 0})
        res['response']['text'] = build_fail_text(curr)
        add_game_over_buttons(res)
        return

    res['response']['text'] = build_wrong_text(state)
    show_rebus(res, state, append_text=False)

def show_history(res, state):
    if not state.get('history'):
        text = f'Пока нет решённых ребусов.\nТекущий счёт: {state["score"]}'
    else:
        lines = [f'{i + 1}. {h["answer"]} → +{h["points"]}' for i, h in enumerate(state['history'])]
        text = '📊 История:\n' + '\n'.join(lines) + f'\n\nИтого: {state["score"]} баллов'
    res['response']['text'] = text
    show_rebus(res, state, append_text=False)

# Создание следующего ребуса
def next_rebus(res, state):
    state['attempts'] = 0
    state['used_hint'] = False
    new_rebus = get_random_rebus_from_pool(state['pool'])
    if new_rebus:
        state['current'] = new_rebus
    else:
        state['current'] = random.choice(state['pool'])
    res['response']['text'] = 'Следующий ребус:'
    show_rebus(res, state)

# Отоброжение ребуса
def show_rebus(res, state, append_text=True):
    rebus = state['current']
    if rebus is None:
        res['response']['text'] = 'Ребусы закончились! Спасибо за игру!'
        res['response']['end_session'] = True
        return

    if append_text and res['response'].get('text'):
        res['response']['text'] += f"\n{rebus['text']}"
    else:
        res['response']['text'] = rebus['text']

    if rebus.get('image_id'):
        res['response']['card'] = {
            'type': 'BigImage',
            'image_id': rebus['image_id'],
            'title': rebus['text']
        }

    add_standard_buttons(res)

# Сохрание результатов игры в базе данных
def save_game_result(user, state):
    user.total_score += state.get('score', 0)
    user.games_played += 1
    user.last_played = datetime.utcnow()
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
