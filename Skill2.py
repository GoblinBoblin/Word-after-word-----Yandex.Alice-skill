from flask import Flask, request, jsonify
import logging
import random

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

REBUSES = [
    {"id": 1, "answer": "ангелина", "hint_letter": "а", "length": 8, "text": "Разгадайте имя", "image_id": "14236656/a28d23c0c73efe1b4013"},
    {"id": 2, "answer": "сосна", "hint_letter": "с", "length": 5, "text": "Что здесь зашифровано?", "image_id": "965417/17343d432e4c1913d2cb"},
    {"id": 3, "answer": "лиса", "hint_letter": "л", "length": 4, "text": "Кто это?", "image_id": "965417/bb148c3bfc4ac6d6b482"},
    {"id": 4, "answer": "волк", "hint_letter": "в", "length": 4, "text": "Отгадайте зверя", "image_id": "1540737/7702ddacd56f9c4cec54"},
    {"id": 5, "answer": "дом", "hint_letter": "д", "length": 3, "text": "Где мы живем?", "image_id": "965417/3b390ee65413c3d34041"},
    {"id": 6, "answer": "кот", "hint_letter": "к", "length": 3, "text": "Домашний зверь", "image_id": "1521359/b97bdebf35d9a4c89f6e"},
    {"id": 7, "answer": "мяч", "hint_letter": "м", "length": 3, "text": "Игрушка", "image_id": "1540737/5e750593cb663009dc74"},
    {"id": 8, "answer": "слон", "hint_letter": "с", "length": 4, "text": "Большое животное", "image_id": "965417/86d46ae8aed8bfde8e60"},
    {"id": 9, "answer": "мишка", "hint_letter": "м", "length": 5, "text": "Лесной житель", "image_id": "1540737/6a9cc3d6e20c1395680e"},
    {"id": 10, "answer": "заяц", "hint_letter": "з", "length": 4, "text": "Длинноухий зверь", "image_id": "965417/9c808ba7bd3a6382620f"},
    {"id": 11, "answer": "рыба", "hint_letter": "р", "length": 4, "text": "Живет в воде", "image_id": "1540737/c952eaf0964bf678d140"},
    {"id": 12, "answer": "птица", "hint_letter": "п", "length": 5, "text": "Умеет летать", "image_id": "1540737/4f6250c1fe3178b29615"},
    {"id": 13, "answer": "маятник", "hint_letter": "м", "length": 7, "text": "Сложный ребус", "image_id": "1540737/48304cde6020c47eba4e"},
    {"id": 14, "answer": "рыбак", "hint_letter": "р", "length": 5, "text": "Человек с удочкой", "image_id": "1540737/27a73d01a07b76fffc73"},
    {"id": 15, "answer": "снегирь", "hint_letter": "с", "length": 7, "text": "Зимняя птица", "image_id": "965417/96c688a72262f19fb641"},
    {"id": 16, "answer": "луноход", "hint_letter": "л", "length": 7, "text": "Космический транспорт", "image_id": "1652229/8c7c98a537963415656a"},
    {"id": 17, "answer": "паровоз", "hint_letter": "п", "length": 7, "text": "Старый поезд", "image_id": "14236656/48b676bc8391145155db"},
    {"id": 18, "answer": "корабль", "hint_letter": "к", "length": 7, "text": "Плывет по морю", "image_id": "965417/761ac00208a3e39cc146"},
    {"id": 19, "answer": "самолет", "hint_letter": "с", "length": 7, "text": "Железная птица", "image_id": "1540737/a80c8f732fd0821cb56b"},
    {"id": 20, "answer": "бегемот", "hint_letter": "б", "length": 7, "text": "Житель Африки", "image_id": "1521359/77bdbaf8554e9500ba20"},
]

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {'end_session': False}
    }
    handle_dialog(response, request.json)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    command = req['request']['command'].lower()

    if req['session']['new']:
        sessionStorage[user_id] = {'mode': 'choose'}
        res['response']['text'] = 'Выберите сложность: легкий (слова до 5 букв) или сложный (длинные слова)'
        # ДОБАВЛЯЕМ КНОПКИ ЗДЕСЬ
        res['response']['buttons'] = [
            {'title': 'Легкий', 'hide': True},
            {'title': 'Сложный', 'hide': True}
        ]
        return

    state = sessionStorage[user_id]

    # === ОТЛОЖЕННЫЙ РЕБУС ===
    if state.get('pending_next'):
        state['pending_next'] = False
        return next_rebus(res, state)

    # === ВЫБОР СЛОЖНОСТИ ===
    if state['mode'] == 'choose':
        if 'легкий' in command:
            state['pool'] = [r for r in REBUSES if r['length'] <= 5]
        elif 'сложный' in command:
            state['pool'] = [r for r in REBUSES if r['length'] > 5]
        else:
            res['response']['text'] = 'Скажите "легкий" или "сложный"'
            return

        state.update({
            'mode': 'game',
            'score': 0,
            'attempts': 0,
            'used_hint': False,
            'history': []
        })

        state['current'] = random.choice(state['pool'])
        return show_rebus(res, state)

    curr = state['current']

    # === ДАЛЬШЕ ===
    if 'дальше' in command:
        return next_rebus(res, state)

    # === ВСЕ ОЧКИ ===
    if 'все очки' in command or 'история' in command:
        if not state['history']:
            res['response']['text'] = 'У вас пока нет очков'
        else:
            lines = [f'{i+1}) {h["answer"]} → +{h["points"]}' for i, h in enumerate(state['history'])]
            res['response']['text'] = '📊 История:\n' + '\n'.join(lines) + f'\n\nИтого: {state["score"]}'
        res['response']['buttons'] = [
            {'title': 'Подсказка', 'hide': True},
            {'title': 'Все очки', 'hide': True},
            {'title': 'Дальше', 'hide': True},
            {'title': 'Выход', 'hide': True}
        ]
        return

    # === ПОДСКАЗКА ===
    if 'подсказка' in command:
        state['used_hint'] = True
        res['response']['text'] = f'Первая буква: {curr["hint_letter"].upper()}'
        res['response']['buttons'] = [
            {'title': 'Подсказка', 'hide': True},
            {'title': 'Все очки', 'hide': True},
            {'title': 'Дальше', 'hide': True},
            {'title': 'Выход', 'hide': True}
        ]
        return

    # === ПРАВИЛЬНО ===
    if command == curr['answer']:
        points = 0 if state['used_hint'] else (2 if state['attempts'] == 0 else 1 if state['attempts'] == 1 else 0)

        state['score'] += points
        state['history'].append({'answer': curr['answer'], 'points': points})

        state['pending_next'] = True

        res['response']['text'] = (
            f'✅ Правильно!\n'
            f'🏅 За задание: {points}\n'
            f'📊 Всего: {state["score"]}\n\n'
            f'Скажите "дальше"'
        )
        return

    # === НЕПРАВИЛЬНО ===
    state['attempts'] += 1

    if state['attempts'] >= 3:
        state['pending_next'] = True
        res['response']['text'] = f'❌ Ответ: {curr["answer"]}\n📊 Очки: {state["score"]}\nСкажите "дальше"'
        return

    res['response']['text'] = f'Неверно. Осталось {3 - state["attempts"]}'
    return show_rebus(res, state)


def next_rebus(res, state):
    state['attempts'] = 0
    state['used_hint'] = False
    state['current'] = random.choice(state['pool'])
    return show_rebus(res, state)


def show_rebus(res, state):
    rebus = state['current']

    res['response']['text'] = rebus['text']

    if rebus.get('image_id'):
        res['response']['card'] = {
            'type': 'BigImage',
            'image_id': rebus['image_id'],
            'title': rebus['text']
        }

    res['response']['buttons'] = [
        {'title': 'Подсказка', 'hide': True},
        {'title': 'Все очки', 'hide': True},
        {'title': 'Дальше', 'hide': True},
        {'title': 'Выход', 'hide': True}
    ]
    return


if __name__ == '__main__':
    app.run()