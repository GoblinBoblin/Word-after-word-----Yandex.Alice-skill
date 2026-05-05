import json
import random
import re
import logging
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
GAME_ROUNDS = 5
POINTS_FIRST = 2
POINTS_SECOND = 1

COMMANDS = {
    'help': ['помощь', 'правила', 'help', 'что делать'],
    'exit': ['выход', 'стоп', 'exit', 'quit', 'завершить'],
    'skip': ['пропустить', 'следующий', 'skip', 'next', 'дальше'],
    'score': ['счет', 'очки', 'score', 'баллы', 'мой счет'],
    'hint': ['подсказка', 'hint', 'подскажи', 'помоги']
}

REBUSES = [
    {"id": 1, "answer": "трава", "aliases": [], "difficulty": 1,
     "hint_letter": "т", "length": 5, "hint_text": "Это то, что растёт на земле.",
     "image_id": "1533899/912eab13f9f043707756",
     "image_text": ""},

    {"id": 2, "answer": "надлом", "aliases": [], "difficulty": 1,
     "hint_letter": "н", "length": 6, "hint_text": "Состояние предмета, который вот-вот сломается.",
     "image_id": "1030494/c50e2681512d73042fd7",
     "image_text": ""},
]

sessions = {}


def normalize_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    return text


def check_answer(user_input, rebus):
    user_norm = normalize_text(user_input)
    if user_norm == normalize_text(rebus['answer']):
        return True
    for alias in rebus.get('aliases', []):
        if user_norm == normalize_text(alias):
            return True
    return False


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


def show_current_rebus(user_id, response):
    session = sessions.get(user_id)
    if not session:
        response['response']['text'] = "Игра не активна."
        return

    rebus = get_rebus(session['current_id'])
    if not rebus:
        start_round(user_id, response)
        return


    if rebus.get('image_id'):
        response['response']['card'] = {
            "type": "BigImage",
            "image_id": rebus['image_id'],
            "title": f"Ребус {session['round']} из {GAME_ROUNDS}",
            "description": f"Попыток осталось: {session['attempts']}"
        }

        response['response']['text'] = (
            f"Ребус {session['round']} из {GAME_ROUNDS}. "
            f"Попыток осталось: {session['attempts']}. "
            f"Какое слово здесь зашифровано?"
        )
    else:
        response['response']['text'] = (
            f"🔍 Ребус {session['round']} из {GAME_ROUNDS}\n\n"
            f"{rebus.get('image_text', 'Ребус')}\n\n"
            f"Попыток: {session['attempts']}\n\n❓ Твой ответ?"
        )

    sessions[user_id] = session


def start_new_game(user_id, response):
    sessions[user_id] = {
        'score': 0, 'round': 0, 'current_id': None,
        'used_ids': [], 'attempts': MAX_ATTEMPTS,
        'hint_used': False, 'correct': 0
    }
    response['response']['text'] = (
        "🎮 Добро пожаловать в игру «Слово за словом»!\n\n"
        "Я буду показывать картинки-ребусы, а ты отгадывай слова.\n\n"
        "**Команды:** подсказка, пропустить, счет, выход, помощь\n\n"
        "Поехали!"
    )
    start_round(user_id, response)


def start_round(user_id, response):
    session = sessions.get(user_id)
    if not session:
        return

    session['round'] += 1

    if session['round'] > GAME_ROUNDS:
        accuracy = (session['correct'] / GAME_ROUNDS) * 100
        response['response']['text'] = (
            f"🎉 Игра завершена!\n🏆 Счёт: {session['score']} очков\n"
            f"🎯 Точность: {accuracy:.0f}%\n\nСпасибо за игру!"
        )
        response['response']['end_session'] = True
        del sessions[user_id]
        return

    rebus = get_random_rebus(session['used_ids'])
    if not rebus:
        response['response']['text'] = "✨ Ребусы закончились!"
        response['response']['end_session'] = True
        del sessions[user_id]
        return

    session['current_id'] = rebus['id']
    session['used_ids'].append(rebus['id'])
    session['attempts'] = MAX_ATTEMPTS
    session['hint_used'] = False
    sessions[user_id] = session

    show_current_rebus(user_id, response)


def process_hint(user_id, response):
    session = sessions.get(user_id)
    if not session:
        response['response']['text'] = "Нет активной игры."
        return
    rebus = get_rebus(session['current_id'])
    if not rebus:
        start_round(user_id, response)
        return
    response['response']['text'] = (
        f"💡 Подсказка: слово начинается на букву '{rebus['hint_letter'].upper()}', "
        f"всего {rebus['length']} букв.\n\n{rebus['hint_text']}"
    )
    session['hint_used'] = True
    sessions[user_id] = session
    show_current_rebus(user_id, response)


def process_answer(user_id, user_input, response):
    session = sessions.get(user_id)
    if not session:
        response['response']['text'] = "Нет активной игры."
        return
    rebus = get_rebus(session['current_id'])
    if not rebus:
        start_round(user_id, response)
        return
    if check_answer(user_input, rebus):
        points = 0
        if not session['hint_used']:
            if session['attempts'] == 3:
                points = POINTS_FIRST
            elif session['attempts'] == 2:
                points = POINTS_SECOND
        session['score'] += points
        session['correct'] += 1
        response['response']['text'] = f"✅ Верно! +{points} очка(ов)."
        if session['round'] >= GAME_ROUNDS:
            response['response']['text'] += f"\n🎉 Игра завершена! Счёт: {session['score']}"
            response['response']['end_session'] = True
            del sessions[user_id]
        else:
            response['response']['text'] += f" Переходим к {session['round'] + 1}-му ребусу."
            start_round(user_id, response)
    else:
        session['attempts'] -= 1
        if session['attempts'] <= 0:
            response['response']['text'] = f"❌ Правильный ответ: «{rebus['answer']}»."
            start_round(user_id, response)
        else:
            response['response']['text'] = f"❌ Неправильно. Осталось попыток: {session['attempts']}."
            show_current_rebus(user_id, response)
        sessions[user_id] = session


def process_score(user_id, response):
    session = sessions.get(user_id)
    if session:
        response['response'][
            'text'] = f"🏆 Счёт: {session['score']} очков. Отгадано: {session['correct']} из {session['round']}"
        show_current_rebus(user_id, response)
    else:
        response['response']['text'] = "Нет активной игры."


def process_skip(user_id, response):
    response['response']['text'] = "⏭️ Пропускаем ребус."
    start_round(user_id, response)


def process_exit(user_id, response):
    session = sessions.get(user_id)
    goodbye = "👋 Спасибо за игру!"
    if session:
        goodbye += f" Твой счёт: {session['score']} очков."
    response['response']['text'] = goodbye
    response['response']['end_session'] = True
    if user_id in sessions:
        del sessions[user_id]


def process_help(user_id, response):
    response['response']['text'] = (
        "📖 Правила:\n"
        "• 1 попытка — 2 очка\n• 2 попытка — 1 очко\n"
        "• После подсказки — 0 очков\n• Всего 5 ребусов\n\n"
        "Команды: подсказка, пропустить, счет, выход, помощь"
    )
    session = sessions.get(user_id)
    if session and session.get('current_id'):
        show_current_rebus(user_id, response)


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
            response['response']['text'] = "Ошибка идентификации."
            return jsonify(response)

        user_command = alice_request.get("request", {}).get("original_utterance", "").lower()
        is_new = alice_request.get("session", {}).get("new", False)

        if is_new or user_id not in sessions:
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
            "response": {"text": "😔 Техническая ошибка. Перезапустите навык.", "end_session": False}
        })


@app.route('/', methods=['GET'])
def health():
    return "Skill is running!", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)