"""
Команды бота. Этот файл — единственное, что нужно редактировать.

Как добавить команду:
  1. Написать async-функцию с сигнатурой (bot, room, event, args)
  2. Добавить запись в COMMANDS
  3. make deploy

bot   — экземпляр MatrixBot (bot.client — AsyncClient, bot._send(room, text))
room  — MatrixRoom (room.room_id, room.display_name, room.users)
event — RoomMessageText (event.sender, event.body)
args  — строка аргументов после команды (может быть пустой)
"""

import asyncio
import random
import re
from datetime import datetime, timezone, timedelta

from storage import load_list, save_list

MSK = timezone(timedelta(hours=3))

# ══════════════════════════════════════════════════════════════
#  Таблица команд: "имя" -> (функция, "описание")
# ══════════════════════════════════════════════════════════════

COMMANDS: dict[str, tuple] = {}


def cmd(name: str, description: str):
    """Декоратор для регистрации команды."""
    def decorator(func):
        COMMANDS[name] = (func, description)
        return func
    return decorator


# ── Работа ────────────────────────────────────────────────────

@cmd("time", "время по МСК")
async def cmd_time(bot, room, event, args):
    now = datetime.now(MSK)
    await bot._send(room, f"Время по МСК: {now.strftime('%H:%M:%S')} ({now.strftime('%d.%m.%Y')})")


@cmd("todo", "добавить задачу")
async def cmd_todo(bot, room, event, args):
    if not args:
        await bot._send(room, "Использование: !todo <текст задачи>")
        return
    items = load_list(room.room_id, "todos")
    items.append({"text": args, "done": False, "by": event.sender})
    save_list(room.room_id, "todos", items)
    await bot._send(room, f"Задача #{len(items)} добавлена: {args}")


@cmd("todos", "список задач")
async def cmd_todos(bot, room, event, args):
    items = load_list(room.room_id, "todos")
    if not items:
        await bot._send(room, "Список задач пуст.")
        return
    lines = ["Задачи:"]
    for i, t in enumerate(items, 1):
        mark = "[x]" if t["done"] else "[ ]"
        lines.append(f"  {i}. {mark} {t['text']}")
    await bot._send(room, "\n".join(lines))


@cmd("done", "отметить задачу выполненной")
async def cmd_done(bot, room, event, args):
    items = load_list(room.room_id, "todos")
    try:
        idx = int(args) - 1
        items[idx]["done"] = True
        save_list(room.room_id, "todos", items)
        await bot._send(room, f"Задача #{idx + 1} выполнена: {items[idx]['text']}")
    except (ValueError, IndexError):
        await bot._send(room, "Использование: !done <номер>")


@cmd("deltodo", "удалить задачу")
async def cmd_deltodo(bot, room, event, args):
    items = load_list(room.room_id, "todos")
    try:
        idx = int(args) - 1
        removed = items.pop(idx)
        save_list(room.room_id, "todos", items)
        await bot._send(room, f"Удалена задача: {removed['text']}")
    except (ValueError, IndexError):
        await bot._send(room, "Использование: !deltodo <номер>")


@cmd("note", "сохранить заметку")
async def cmd_note(bot, room, event, args):
    if not args:
        await bot._send(room, "Использование: !note <текст заметки>")
        return
    items = load_list(room.room_id, "notes")
    now = datetime.now(MSK).strftime("%d.%m %H:%M")
    items.append({"text": args, "by": event.sender, "at": now})
    save_list(room.room_id, "notes", items)
    await bot._send(room, f"Заметка #{len(items)} сохранена.")


@cmd("notes", "список заметок")
async def cmd_notes(bot, room, event, args):
    items = load_list(room.room_id, "notes")
    if not items:
        await bot._send(room, "Заметок нет.")
        return
    lines = ["Заметки:"]
    for i, n in enumerate(items, 1):
        lines.append(f"  {i}. [{n['at']}] {n['text']}")
    await bot._send(room, "\n".join(lines))


@cmd("delnote", "удалить заметку")
async def cmd_delnote(bot, room, event, args):
    items = load_list(room.room_id, "notes")
    try:
        idx = int(args) - 1
        removed = items.pop(idx)
        save_list(room.room_id, "notes", items)
        await bot._send(room, f"Удалена заметка: {removed['text']}")
    except (ValueError, IndexError):
        await bot._send(room, "Использование: !delnote <номер>")


@cmd("remind", "напоминание через N минут")
async def cmd_remind(bot, room, event, args):
    match = re.match(r"(\d+)\s+(.+)", args)
    if not match:
        await bot._send(room, "Использование: !remind <минуты> <текст>")
        return
    minutes = int(match.group(1))
    text = match.group(2)
    sender = event.sender
    await bot._send(room, f"Напомню через {minutes} мин: {text}")

    async def _fire():
        await asyncio.sleep(minutes * 60)
        await bot._send(room, f"Напоминание для {sender}: {text}")

    asyncio.ensure_future(_fire())


@cmd("pick", "рандомный участник комнаты")
async def cmd_pick(bot, room, event, args):
    members = [uid for uid in room.users if uid != bot.client.user_id]
    if not members:
        await bot._send(room, "В комнате никого кроме меня.")
        return
    chosen = random.choice(members)
    name = room.user_name(chosen) or chosen
    await bot._send(room, f"Выбираю... {name} ({chosen})")


@cmd("countdown", "дней до дедлайна")
async def cmd_countdown(bot, room, event, args):
    match = re.match(r"(\d{1,2}\.\d{1,2}\.\d{4})\s*(.*)", args)
    if not match:
        await bot._send(room, "Использование: !countdown ДД.ММ.ГГГГ название")
        return
    try:
        target = datetime.strptime(match.group(1), "%d.%m.%Y").replace(tzinfo=MSK)
    except ValueError:
        await bot._send(room, "Неверный формат даты. Пример: 01.06.2026")
        return
    label = match.group(2).strip() or "дедлайн"
    delta = (target - datetime.now(MSK)).days
    if delta < 0:
        await bot._send(room, f"{label} был {abs(delta)} дн. назад.")
    elif delta == 0:
        await bot._send(room, f"{label} — СЕГОДНЯ!")
    else:
        await bot._send(room, f"До «{label}» осталось {delta} дн.")


# ── Фан ──────────────────────────────────────────────────────

QUOTES = [
    "Talk is cheap. Show me the code. — Linus Torvalds",
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. — Martin Fowler",
    "First, solve the problem. Then, write the code. — John Johnson",
    "Code is like humor. When you have to explain it, it's bad. — Cory House",
    "Make it work, make it right, make it fast. — Kent Beck",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "It's not a bug — it's an undocumented feature. — Anonymous",
    "Deleted code is debugged code. — Jeff Sickel",
    "Weeks of coding can save you hours of planning. — Anonymous",
    "The best error message is the one that never shows up. — Thomas Fuchs",
]

JOKES = [
    "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 == Dec 25.",
    "— Сколько программистов нужно, чтобы вкрутить лампочку?\n— Ни одного, это аппаратная проблема.",
    "Два самых сложных дела в программировании: инвалидация кэша, именование переменных и ошибка на единицу.",
    "git commit -m \"fixed it\"\n...5 минут спустя...\ngit commit -m \"actually fixed it\"",
    "Программист: \"Работает на моей машине.\"\nDevOps: \"Тогда деплоим твою машину.\"",
    "// TODO: исправить потом\n// Написано 3 года назад",
    "Три стадии дебага:\n1. Это невозможно.\n2. Это не должно происходить.\n3. О, я забыл точку с запятой.",
]

MAGIC_8BALL = [
    "Бесспорно", "Определённо да", "Можешь быть уверен", "Вероятнее всего",
    "Да", "Знаки говорят — да", "Пока не ясно, попробуй снова",
    "Спроси позже", "Сейчас нельзя предсказать",
    "Даже не думай", "Мой ответ — нет", "Весьма сомнительно",
]


@cmd("hello", "вечер в хату")
async def cmd_hello(bot, room, event, args):
    await bot._send(room, "Вечер в хату!")


@cmd("8ball", "магический шар")
async def cmd_8ball(bot, room, event, args):
    if not args:
        await bot._send(room, "Задай вопрос: !8ball будет ли релиз вовремя?")
        return
    await bot._send(room, f"Магический шар: {random.choice(MAGIC_8BALL)}")


@cmd("flip", "монетка")
async def cmd_flip(bot, room, event, args):
    await bot._send(room, f"Монетка: {'Орёл' if random.randint(0, 1) else 'Решка'}")


@cmd("dice", "кубики [NdM]")
async def cmd_dice(bot, room, event, args):
    match = re.match(r"(\d+)d(\d+)", args.strip()) if args.strip() else None
    n, sides = (min(int(match.group(1)), 20), min(int(match.group(2)), 1000)) if match else (1, 6)
    rolls = [random.randint(1, sides) for _ in range(n)]
    total = sum(rolls)
    if n > 1:
        await bot._send(room, f"Кубики ({n}d{sides}): {' + '.join(map(str, rolls))} = {total}")
    else:
        await bot._send(room, f"Кубик (1d{sides}): {total}")


@cmd("quote", "цитата про код")
async def cmd_quote(bot, room, event, args):
    await bot._send(room, random.choice(QUOTES))


@cmd("joke", "шутка для девов")
async def cmd_joke(bot, room, event, args):
    await bot._send(room, random.choice(JOKES))
