---
name: setup-media-storage
description: >
  Развёртывание медиа-хранилища для контент-завода: Cloudflare R2 + универсальный
  скрипт pixel_upload.py для генерации изображений/видео и загрузки в S3-совместимое
  хранилище. Используй этот скилл когда пользователь хочет: настроить хранилище для
  медиа-контента агентов, подключить Cloudflare R2 к контент-заводу, развернуть
  Pixel pipeline (fal.ai / Replicate → R2), добавить pixel_upload.py в shared/scripts,
  настроить визуальные стили для блогеров, или обновить openclaw.json чтобы убрать
  старые pixel-* агенты и оставить один универсальный pixel.
---

# Skill: Setup Media Storage (Cloudflare R2 + Pixel Pipeline)

## Контекст

Контент-завод хранит медиа в Cloudflare R2 — S3-совместимом хранилище без egress fees,
работающем из РФ через Cloudflare CDN. Один универсальный агент `pixel` генерирует
медиа для всех блогеров и площадок, читая визуальные правила из
`shared/bloggers/{blogger}/brand/visual-{platform}.md`.

## Структура хранилища

```
R2 бакеты:
  media-raw        ← сырой output Pixel (TTL 30 дней)
  media-approved   ← после ревью директора (публичный доступ, CDN)
  media-published  ← после публикации (аудит-лог, TTL 1 год)

Naming convention:
  {blogger}/{YYYY-MM-DD}/{job_id}/{type}_{uuid}.{ext}
  пример: tomas/2025-06-12/post-042/image_a3f9c.jpg
```

## Шаг 1 — Создать бакеты в Cloudflare R2

Только через dashboard (нет CLI):

1. `dash.cloudflare.com` → R2 → **Create bucket**
2. Создать три бакета: `media-raw`, `media-approved`, `media-published`
3. Location: **Automatic**, Storage Class: **Standard**
4. Для `media-raw`: открыть бакет → **Settings** → **Public access** → **Allow Access**
5. Скопировать публичный URL вида `https://pub-XXXXXXXX.r2.dev`

## Шаг 2 — Получить R2 credentials

`dash.cloudflare.com` → R2 → **Manage R2 API Tokens** → **Create API Token**
- Permissions: Object Read & Write
- Apply to: All buckets

Сохранить сразу — Secret Access Key показывается один раз:
- `Access Key ID` → `R2_ACCESS_KEY_ID`
- `Secret Access Key` → `R2_SECRET_ACCESS_KEY`
- Account ID — в правом сайдбаре любой страницы Cloudflare → `R2_ACCOUNT_ID`

## Шаг 3 — Заполнить .env

```bash
nano ~/dev/projects/agents/content-factory/.env
```

Добавить в конец:

```
# ─── Cloudflare R2 ───────────────────────────────────
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_RAW=media-raw
R2_PUBLIC_URL=https://pub-XXXXXXXX.r2.dev

# ─── Генерация медиа ─────────────────────────────────
FAL_KEY=
REPLICATE_API_TOKEN=
KLING_API_KEY=
RUNWAYML_API_SECRET=
```

**Важно:** fal_client читает переменную `FAL_KEY`, не `FAL_API_KEY`.

## Шаг 4 — Разложить файлы

```bash
cd ~/dev/projects/agents/content-factory

# Создать папку для скриптов если нет
mkdir -p shared/scripts

# Скопировать скрипт генерации
cp pixel_upload.py shared/scripts/pixel_upload.py

# Визуальный стиль блогера (пример для Томаса / TG)
cp visual-tg-tomas-food.md shared/bloggers/tomas/brand/visual-tg.md
```

## Шаг 5 — Установить зависимости

```bash
pip3 install boto3 fal-client
# replicate опционально (fallback для фото)
pip3 install replicate
```

На macOS флаг `--break-system-packages` не нужен.

## Шаг 6 — Проверить загрузку

```bash
cd ~/dev/projects/agents/content-factory
source .env
export FAL_KEY=$FAL_KEY  # убедиться что в окружении

python3 shared/scripts/pixel_upload.py \
  --job_id test-001 \
  --blogger tomas \
  --platform tg \
  --prompt_file shared/bloggers/tomas/jobs/YYYYMMDD-001/image_prompt.txt
```

Успешный вывод:
```
[Pixel] tomas/tg/test-001
[Pixel] fal.ai flux-dev...
[Pixel] 3.8с, 89кб → R2...
PIXEL_URL: https://pub-XXXXXXXX.r2.dev/tomas/2025-06-12/test-001/image_6ff765cd.jpg
```

Открыть URL в браузере — должна открыться картинка.

## Шаг 7 — Обновить openclaw.json

Убрать старые `pixel-*` агенты, добавить один универсальный `pixel`:

```bash
# Удалить все pixel-* агенты
python3 -c "
import json
with open('$HOME/.openclaw/openclaw.json') as f:
    d = json.load(f)
remove = {a['id'] for a in d['agents']['list'] if a['id'].startswith('pixel-')}
d['agents']['list'] = [a for a in d['agents']['list'] if a['id'] not in remove]
with open('$HOME/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print('Удалены:', remove)
"

# Добавить единственный pixel
python3 -c "
import json
with open('$HOME/.openclaw/openclaw.json') as f:
    d = json.load(f)
d['agents']['list'].append({
    'id': 'pixel',
    'workspace': '/home/node/.openclaw/workspace-pixel',
    'model': 'minimax/minimax-m2.7'
})
with open('$HOME/.openclaw/openclaw.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print('Done')
"
```

## Шаг 8 — Задеплоить SOUL.md и обновить конфиги

```bash
# SOUL.md для pixel агента
mkdir -p ~/.openclaw/workspace-pixel
cp souls/pixel.md ~/.openclaw/workspace-pixel/SOUL.md

# Убрать старые pixel-* из 3-configure.sh, оставить только один (если ещё остались)
sed -i '' '/deploy_soul "pixel-misha-yt"/d' scripts/3-configure.sh
sed -i '' '/deploy_soul "pixel-yulya-ig"/d' scripts/3-configure.sh
sed -i '' '/deploy_soul "pixel-nasik-tt"/d' scripts/3-configure.sh

# Проверить что осталась только одна строка
grep "pixel" scripts/3-configure.sh
# Ожидаемый результат: deploy_soul "pixel" "pixel.md"

# Обновить ROUTING.md директора — заменить все pixel-* на pixel
nano ~/.openclaw/workspace-director/ROUTING.md
cp ~/.openclaw/workspace-director/ROUTING.md souls/routing-director.md

# Перезапустить и зафиксировать
docker compose restart openclaw-gateway
git add -A
git commit -m "pixel: R2 storage setup, single universal pixel agent"
```

## Платформы и API генерации

| platform | тип | primary API | fallback |
|----------|-----|-------------|----------|
| `tg` | фото 1:1 | fal.ai flux-dev | Replicate flux-dev |
| `reels` | видео 9:16 | Kling v1 | RunwayML Gen-3 |
| `shorts` | видео 9:16 | Kling v1 | RunwayML Gen-3 |
| `tt` | видео 9:16 | Kling v1 | RunwayML Gen-3 |

## Частые проблемы

**`No module named 'fal_client'`** → `pip3 install fal-client`

**`No credentials found. Set FAL_KEY`** → fal_client читает `FAL_KEY`, не `FAL_API_KEY`:
```bash
export FAL_KEY=твой_ключ
```
И в `.env` использовать `FAL_KEY=`, не `FAL_API_KEY=`.

**`Exhausted balance`** — пополнить баланс на `fal.ai/dashboard/billing`

**`source .env` не подхватывает переменные** — использовать:
```bash
export $(grep -v '^#' .env | xargs)
```

**`No such file or directory: shared/scripts`** — создать папку:
```bash
mkdir -p shared/scripts
```

**Переменные R2 не загружаются после редактирования .env** — повторить `source .env` или `export $(grep -v '^#' .env | xargs)`.

## Структура файлов после деплоя

```
content-factory/
├── shared/
│   ├── scripts/
│   │   └── pixel_upload.py        ← универсальный скрипт генерации
│   ├── platform-specs/
│   │   ├── telegram.md
│   │   ├── instagram-reels.md
│   │   ├── youtube-shorts.md
│   │   └── tiktok.md
│   └── bloggers/
│       └── {blogger}/brand/
│           └── visual-{platform}.md   ← визуальный стиль блогера
└── souls/
    └── pixel.md                   ← SOUL.md универсального агента
```
