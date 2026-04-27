#!/bin/bash
# llm-gen.sh "опиши промпт" > script.sh
# Пример: ./llm-gen.sh "создай скрипт бэкапа" > backup.sh

set -euo pipefail

PROMPT="${1:-}"
MODEL="qwen3.5:latest"

if [[ -z "$PROMPT" ]]; then
  echo "Использование: $0 \"описание скрипта\" > output.sh" >&2
  exit 1
fi

SYSTEM="Ты — генератор bash-скриптов. Отвечай только кодом без пояснений. Скрипт должен содержать shebang, set -euo pipefail, обработку аргументов, логирование."

# Формируем JSON без переносов в строках
curl -s --max-time 30000 "http://192.168.0.161:11434/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"$SYSTEM\"},
      {\"role\": \"user\", \"content\": \"$PROMPT\"}
    ],
    \"temperature\": 0.2,
    \"max_tokens\": 4096
  }"
