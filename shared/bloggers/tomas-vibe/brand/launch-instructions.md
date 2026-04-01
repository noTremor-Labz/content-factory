# Launch Instructions — tomas

## Каналы
- food: -1001922231049
- vibe: -1003768027613

## Bot Token
8791844060:AAEY6cZt-CmanY3jyw6ui1tqRSHrAN-wUzA

## Публикация
curl -s -X POST "https://api.telegram.org/bot{TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":\"{CHANNEL_ID}\",\"text\":\"{TEXT}\",\"parse_mode\":\"HTML\"}"
