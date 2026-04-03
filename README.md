# Matrix Bot Framework

Инструмент для создания и деплоя ботов в Matrix.
Работает с любым Synapse-сервером в Docker.

```
make install    — установить зависимости
make register   — зарегистрировать бота на сервере
make deploy     — задеплоить
```

## Быстрый старт

### 1. Настроить

```bash
cp .env.example .env
nano .env
```

Заполнить:

```env
HOMESERVER_URL=https://matrix.example.org     # URL сервера
HOMESERVER_DOMAIN=example.org                 # Домен (часть после @ в user_id)
BOT_USERNAME=mybot                            # Логин бота
BOT_PASSWORD=strongpassword                   # Пароль бота
BOT_DISPLAY_NAME=My Bot                       # Имя в чате

SSH_HOST=1.2.3.4                              # IP сервера
SSH_USER=root                                 # SSH юзер
SSH_PASSWORD=xxx                              # SSH пароль (или SSH_KEY)
REGISTRATION_SHARED_SECRET=xxx                # Из homeserver.yaml
```

Shared secret найти:

```bash
ssh root@SERVER "grep registration_shared_secret PATH/data/synapse/homeserver.yaml"
```

### 2. Установить зависимости

```bash
make install
```

### 3. Зарегистрировать бота

```bash
make register
```

### 4. Задеплоить

```bash
make deploy
```

### 5. Добавить бота в комнату

В Element: **Комната → Участники → Пригласить → `@mybot:example.org`**

Бот автоматически примет инвайт.

## Добавить команду

Единственный файл, который нужно редактировать — `commands.py`.

```python
@cmd("mycommand", "описание для !help")
async def cmd_mycommand(bot, room, event, args):
    await bot._send(room, f"Привет, {event.sender}!")
```

Три строки — и команда `!mycommand` работает. Деплой:

```bash
make deploy
```

### Доступные объекты в команде

| Аргумент | Что это | Полезные поля |
|---|---|---|
| `bot` | Экземпляр бота | `bot.client` — AsyncClient, `bot._send(room, text)` |
| `room` | Комната | `room.room_id`, `room.display_name`, `room.users` |
| `event` | Сообщение | `event.sender`, `event.body` |
| `args` | Текст после команды | Строка, может быть пустой |

### Хранить данные между перезапусками

```python
from storage import load_list, save_list

items = load_list(room.room_id, "my_data")    # загрузить
items.append({"key": "value"})
save_list(room.room_id, "my_data", items)      # сохранить
```

Данные хранятся отдельно для каждой комнаты в `bot_data/`.

## Структура проекта

```
commands.py         ← РЕДАКТИРОВАТЬ: все команды бота
storage.py          ← хранилище данных (load_list / save_list)
config.py           ← чтение .env
bot.py              ← фреймворк (не трогать)
register_bot.py     ← регистрация юзера через SSH
deploy.sh           ← деплой через SSH + Docker
Makefile            ← короткие команды
Dockerfile          ← образ контейнера
docker-compose.yml  ← запуск контейнера
.env.example        ← шаблон настроек
.env                ← настройки (не коммитить)
```

## Команды make

| Команда | Что делает |
|---|---|
| `make install` | Установить Python-зависимости |
| `make register` | Зарегистрировать бота на сервере |
| `make deploy` | Деплой (мягкий — build + restart) |
| `make deploy-hard` | Деплой (полный — down + build + up + prune) |
| `make logs` | Показать логи бота на сервере |
| `make restart` | Перезапустить бота |
| `make reset` | Сбросить сессию (удалить ключи, перелогин) |

## Встроенные команды

### Работа

| Команда | Описание |
|---|---|
| `!time` | Время по МСК |
| `!todo <текст>` | Добавить задачу |
| `!todos` | Список задач |
| `!done <#>` | Выполнить задачу |
| `!deltodo <#>` | Удалить задачу |
| `!note <текст>` | Сохранить заметку |
| `!notes` | Список заметок |
| `!delnote <#>` | Удалить заметку |
| `!remind <мин> <текст>` | Напоминание через N минут |
| `!pick` | Рандомный участник |
| `!countdown ДД.ММ.ГГГГ текст` | Дней до дедлайна |

### Фан

| Команда | Описание |
|---|---|
| `!hello` | Вечер в хату! |
| `!8ball <вопрос>` | Магический шар |
| `!flip` | Монетка |
| `!dice [NdM]` | Кубики |
| `!quote` | Цитата про код |
| `!joke` | Шутка |

`!help` генерируется автоматически из зарегистрированных команд.

## Требования

- Python 3.12+
- Docker + Docker Compose на сервере
- Synapse в Docker
- `sshpass` (`brew install hudochenkov/sshpass/sshpass` / `apt install sshpass`)

## Перенос на другой сервер

1. Скопировать проект
2. Заполнить `.env` данными нового сервера
3. `make register && make deploy`
