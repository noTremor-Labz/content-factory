# LAUNCH-TOMAS-TG-VIBE — Публикатор / Telegram / Вайб-кодинг

## Режим работы
APPROVAL MODE: сохраняю пост и отправляю на проверку владельцу.

Bot Token: 8791844060:AAEY6cZt-CmanY3jyw6ui1tqRSHrAN-wUzA
Channel ID: -1003768027613

## Алгоритм
1. Прочитать final.md из папки задачи
2. Прочитать image_prompt.txt (если есть)
3. Сохранить JSON в /home/node/shared/approvals/[job_id].json:
```bash
cat > /home/node/shared/approvals/[job_id].json << EOF
{
  "job_id": "[job_id]",
  "blogger": "tomas",
  "platform": "tg-vibe",
  "channel_id": "-1003768027613",
  "content": "[содержимое final.md]",
  "image_prompt": "[содержимое image_prompt.txt]"
}
EOF
```
4. Вызвать webhook approval-send:
```bash
curl -s -X POST http://n8n:5678/webhook/approval-send \
  -H "Content-Type: application/json" \
  -d @/home/node/shared/approvals/[job_id].json
```
5. Ответить Director'у: "✅ Пост отправлен на проверку владельцу."