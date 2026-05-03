# skill.py - Навык для Алисы "Слово за словом"
# Запуск: нажмите Ctrl+Shift+F10

import json
import random
import re
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# ==================== НАСТРОЙКА ====================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== КОНСТАНТЫ ====================
MAX_ATTEMPTS = 3
GAME_ROUNDS = 5
POINTS_FIRST = 2
POINTS_SECOND = 1
POINTS_THIRD = 0

# ==================== КОМАНДЫ ====================
COMMANDS = {
    'help': ['помощь', 'правила', 'help'],
    'exit': ['выход', 'стоп', 'exit', 'quit'],
    'skip': ['пропустить', 'следующий', 'skip', 'next'],
    'score': ['счет', 'очки', 'score'],
    'hint': ['подсказка', 'hint']
}

# ==================== БАЗА РЕБУСОВ ====================
REBUSES = [
    {"id": 1, "answer": "ангелина", "hint_letter": "а", "length": 8, "text": "🧩 На картинке: АНГЕЛ + буква И"},
    {"id": 2, "answer": "сосна", "hint_letter": "с", "length": 5, "text": "🧩 На картинке: СОСНА + буква А"},
    {"id": 3, "answer": "лиса", "hint_letter": "л", "length": 4, "text": "🧩 На картинке: ЛИСА + буква З"},
    {"id": 4, "answer": "волк", "hint_letter": "в", "length": 4, "text": "🧩 На картинке: ВОЛК + буква Б"},
    {"id": 5, "answer": "дом", "hint_letter": "д", "length": 3, "text": "🧩 На картинке: ДОМ + буква М"},
    {"id": 6, "answer": "кот", "hint_letter": "к", "length": 3, "text": "🧩 На картинке: КОТ + буква К"},
    {"id": 7, "answer": "мяч", "hint_letter": "м", "length": 3, "text": "🧩 На картинке: МЯЧ + буква Ч"},
    {"id": 8, "answer": "слон", "hint_letter": "с", "length": 4, "text": "🧩 На картинке: СЛОН + буква Н"},
    {"id": 9, "answer": "мишка", "hint_letter": "м", "length": 5, "text": "🧩 На картинке: МИШКА + буква Ш"},
    {"id": 10, "answer": "заяц", "hint_letter": "з", "length": 4, "text": "🧩 На картинке: ЗАЯЦ + буква Ц"},
    {"id": 11, "answer": "рыба", "hint_letter": "р", "length": 4, "text": "🧩 На картинке: РЫБА + буква Б"},
    {"id": 12, "answer": "птица", "hint_letter": "п", "length": 5, "text": "🧩 На картинке: ПТИЦА + буква Ц"},
    {"id": 13, "answer": "маятник", "hint_letter": "м", "length": 7, "text": "🧩 На картинке: МАЯТНИК + буква Я"},
    {"id": 14, "answer": "рыбак", "hint_letter": "р", "length": 5, "text": "🧩 На картинке: РЫБА + буква К"},
    {"id": 15, "answer": "снегирь", "hint_letter": "с", "length": 7, "text": "🧩 На картинке: СНЕГИРЬ + буква Г"},
    {"id": 16, "answer": "луноход", "hint_letter": "л", "length": 7, "text": "🧩 На картинке: ЛУНА + слово ХОД"},
    {"id": 17, "answer": "паровоз", "hint_letter": "п", "length": 7, "text": "🧩 На картинке: ПАР + слово ВОЗ"},
    {"id": 18, "answer": "корабль", "hint_letter": "к", "length": 7, "text": "🧩 На картинке: КОРА + буква Б"},
    {"id": 19, "answer": "самолет", "hint_letter": "с", "length": 7, "text": "🧩 На картинке: САМ + слово ЛЕТ"},
    {"id": 20, "answer": "бегемот", "hint_letter": "б", "length": 7, "text": "🧩 На картинке: БЕГ + буква М"},
]

# ==================== ХРАНИЛИЩЕ СЕССИЙ ====================
sessions = {}


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def normalize(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    return text


def check_answer(user_input, correct):
    return normalize(user_input) == normalize(correct)


def get_rebus(rebus_id):
    for r in REBUSES:
        if r['id'] == rebus_id:
            return r
    return None


def get_random_rebus(exclude_ids):
    available = [r for r in REBUSES if r['id'] not in exclude_ids]
    return random.choice(available) if available else None


def parse_command(text):
    text_lower = text.lower()
    for cmd, keywords in COMMANDS.items():
        for kw in keywords:
            if kw in text_lower:
                return cmd
    return None


# ==================== ИГРОВАЯ ЛОГИКА ====================
def start_new_game(user_id, response):
    sessions[user_id] = {
        'score': 0,
        'round': 0,
        'current_id': None,
        'used_ids': [],
        'attempts': MAX_ATTEMPTS,
        'hint_used': False,
        'correct': 0
    }
    response['response'][
        'text'] = "🎮 Добро пожаловать в игру «Слово за словом»!\n\n📖 Отгадывай ребусы, получай очки. Команды: подсказка, пропустить, счет, выход, помощь.\n\nПоехали!"
    start_round(user_id, response)


def start_round(user_id, response):
    session = sessions.get(user_id)
    if not session:
        return

    session['round'] += 1

    if session['round'] > GAME_ROUNDS:
        accuracy = (session['correct'] / GAME_ROUNDS) * 100
        response['response'][
            'text'] = f"🎉 ИГРА ЗАВЕРШЕНА!\n🏆 Счет: {session['score']} очков\n🎯 Точность: {accuracy:.0f}%\n\nСпасибо за игру!"
        response['response']['end_session'] = True
        del sessions[user_id]
        return

    rebus = get_random_rebus(session['used_ids'])
    if not rebus:
        response['response']['text'] = "Ребусы закончились! Игра завершена."
        response['response']['end_session'] = True
        del sessions[user_id]
        return

    session['current_id'] = rebus['id']
    session['used_ids'].append(rebus['id'])
    session['attempts'] = MAX_ATTEMPTS
    session['hint_used'] = False

    response['response'][
        'text'] = f"🔍 {rebus['text']}\n\n📊 Ребус {session['round']} из {GAME_ROUNDS}\n🎯 Попыток: {session['attempts']}\n\n❓ Какое слово зашифровано?"


def show_current_rebus(user_id, response):
    session = sessions.get(user_id)
    if not session:
        return
    rebus = get_rebus(session['current_id'])
    if rebus:
        response['response'][
            'text'] = f"{rebus['text']}\n\n📊 Ребус {session['round']} из {GAME_ROUNDS}\n🎯 Попыток: {session['attempts']}\n\n❓ Какое слово?"


def process_hint(user_id, response):
    session = sessions.get(user_id)
    if not session:
        response['response']['text'] = "Игра не активна"
        return

    if session['hint_used']:
        response['response']['text'] = "💡 Подсказка уже была использована для этого ребуса."
        show_current_rebus(user_id, response)
        return

    rebus = get_rebus(session['current_id'])
    if rebus:
        response['response'][
            'text'] = f"💡 Подсказка: слово начинается на букву «{rebus['hint_letter'].upper()}», всего {rebus['length']} букв."
        session['hint_used'] = True
        show_current_rebus(user_id, response)


def process_score(user_id, response):
    session = sessions.get(user_id)
    if session:
        response['response'][
            'text'] = f"🏆 Твой счет: {session['score']} очков. Отгадано слов: {session['correct']} из {session['round']}."
        show_current_rebus(user_id, response)
    else:
        response['response']['text'] = "Игра не активна"


def process_skip(user_id, response):
    response['response']['text'] = "⏭️ Пропускаем этот ребус."
    start_round(user_id, response)


def process_exit(user_id, response):
    session = sessions.get(user_id)
    if session:
        response['response']['text'] = f"👋 Спасибо за игру! Твой финальный счет: {session['score']} очков."
    else:
        response['response']['text'] = "👋 До свидания!"
    response['response']['end_session'] = True
    if user_id in sessions:
        del sessions[user_id]


def process_help(user_id, response):
    response['response']['text'] = """📖 **Правила игры:**
• Я загадываю слово в виде ребуса
• Ты называешь зашифрованное слово
• За ответ с 1 попытки — 2 очка
• Со 2 попытки — 1 очко
• После подсказки или 3 ошибки — 0 очков
• Всего 5 ребусов

**Команды:**
• «подсказка» — первая буква и длина
• «пропустить» — следующий ребус
• «счет» — текущие очки
• «выход» — завершить игру
• «помощь» — правила"""

    session = sessions.get(user_id)
    if session and session.get('current_id'):
        show_current_rebus(user_id, response)


def process_answer(user_id, user_input, response):
    session = sessions.get(user_id)
    if not session:
        response['response']['text'] = "Игра не активна. Скажите «запусти навык Слово за словом»"
        return

    rebus = get_rebus(session['current_id'])
    if not rebus:
        start_round(user_id, response)
        return

    if check_answer(user_input, rebus['answer']):
        points = 0
        if not session['hint_used']:
            if session['attempts'] == 3:
                points = POINTS_FIRST
            elif session['attempts'] == 2:
                points = POINTS_SECOND

        session['score'] += points
        session['correct'] += 1

        response['response']['text'] = f"✅ Верно! Это слово «{rebus['answer']}». +{points} очка(ов)."

        if session['round'] >= GAME_ROUNDS:
            accuracy = (session['correct'] / GAME_ROUNDS) * 100
            response['response'][
                'text'] += f"\n\n🎉 ИГРА ЗАВЕРШЕНА!\n🏆 Итоговый счет: {session['score']} очков\n🎯 Точность: {accuracy:.0f}%"
            response['response']['end_session'] = True
            del sessions[user_id]
        else:
            response['response']['text'] += " Переходим к следующему ребусу."
            start_round(user_id, response)
    else:
        session['attempts'] -= 1

        if session['attempts'] <= 0:
            response['response']['text'] = f"❌ Правильный ответ: «{rebus['answer']}». Переходим дальше."
            start_round(user_id, response)
        else:
            response['response']['text'] = f"❌ Неправильно. Осталось попыток: {session['attempts']}."
            show_current_rebus(user_id, response)


# ==================== FLASK-СЕРВЕР ====================
@app.route('/post', methods=['POST'])
def alice_webhook():
    try:
        alice_request = request.json
        logger.info(f"Запрос от: {alice_request.get('session', {}).get('user_id')}")

        response = {
            "session": alice_request.get("session", {}),
            "version": alice_request.get("version", "1.0"),
            "response": {"end_session": False}
        }

        user_id = alice_request.get("session", {}).get("user_id")
        if not user_id:
            response['response']['text'] = "Ошибка идентификации"
            return jsonify(response)

        user_command = alice_request.get("request", {}).get("original_utterance", "").lower()
        is_new = alice_request.get("session", {}).get("new", False)

        if is_new:
            start_new_game(user_id, response)
            return jsonify(response)

        if user_id not in sessions:
            start_new_game(user_id, response)
            return jsonify(response)

        cmd = parse_command(user_command)

        if cmd == 'help':
            process_help(user_id, response)
        elif cmd == 'exit':
            process_exit(user_id, response)
        elif cmd == 'skip':
            process_skip(user_id, response)
        elif cmd == 'score':
            process_score(user_id, response)
        elif cmd == 'hint':
            process_hint(user_id, response)
        else:
            process_answer(user_id, user_command, response)

        return jsonify(response)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({
            "session": request.json.get("session", {}) if request.json else {},
            "version": "1.0",
            "response": {"text": "😔 Ошибка, перезапустите навык", "end_session": False}
        })


@app.route('/', methods=['GET'])
def health():
    return "Skill is running!", 200


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🎮 НАВЫК ЗАПУЩЕН")
    print("=" * 50)
    print("\n🚀 Сервер: http://127.0.0.1:5000")
    print("\n📌 В ОТДЕЛЬНОМ ОКНЕ PowerShell выполните:")
    print("   tuna http 5000")
    print("\n📌 Ссылку из tuna вставьте в Яндекс.Диалоги")
    print("   (добавьте в конце /post)")
    print("=" * 50 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)