.PHONY: install register deploy deploy-hard logs restart reset help

help: ## Показать эту справку
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-14s %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

register: ## Зарегистрировать бот-юзера на сервере
	python3 register_bot.py

deploy: ## Деплой на сервер (мягкий)
	./deploy.sh

deploy-hard: ## Деплой на сервер (полный пересбор)
	./deploy.sh hard

logs: ## Логи бота на сервере
	@. ./.env 2>/dev/null; sshpass -p "$$SSH_PASSWORD" ssh -T -o StrictHostKeyChecking=accept-new root@$$SSH_HOST "cd /root/matrix-bot && docker compose logs --tail 50"

restart: ## Перезапустить бота на сервере
	@. ./.env 2>/dev/null; sshpass -p "$$SSH_PASSWORD" ssh -T -o StrictHostKeyChecking=accept-new root@$$SSH_HOST "cd /root/matrix-bot && docker compose restart"

reset: ## Сбросить сессию бота (удалить ключи и credentials)
	@. ./.env 2>/dev/null; sshpass -p "$$SSH_PASSWORD" ssh -T -o StrictHostKeyChecking=accept-new root@$$SSH_HOST "cd /root/matrix-bot && rm -rf nio_store credentials.json && docker compose restart"
	@echo "Сессия сброшена. Бот создаст новую при следующем запуске."
