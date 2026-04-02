# Роутинг агентов по блогерам и каналам

## Quill (универсально)
- Агент OpenClaw: **`quill`** (один на всех блогеров), workspace `workspace-quill`. Голос и стиль — из `/home/node/shared/bloggers/{blogger}/brand/` для переданного `blogger`; отдельные агенты `quill-*` не используются.

## Редактор Lens (универсально)
- Агент OpenClaw: **`lens`** (один на всех блогеров), workspace `workspace-lens`.
- Стиль и критерии — только из `/home/node/shared/bloggers/{blogger}/brand/` для переданного `blogger`; отдельные агенты `lens-*` не используются.

## tomas-food
- platform: tg
- pipeline: quill → lens(text) → lens(prompt) → pixel(generate) → lens(image) → launch  
  (параллельно после ресёрча: quill + pixel только `image_prompt.txt`)

## tomas-vibe
- platform: tg
- pipeline: как у tomas-food

## misha
- platform: yt
- pipeline: quill → lens(text) → lens(prompt) → pixel(generate) → lens(image) → launch

## yulya
- platform: ig
- pipeline: quill → lens(text) → lens(prompt) → pixel(generate) → lens(image) → launch

## nasik
- platform: tt
- pipeline: quill → lens(text) → lens(prompt) → pixel(generate) → lens(image) → launch

## Формат задачи для Director'а
тема: [тема] | платформа: [tg|yt|ig|tt] | формат: пост | блогер: [tomas-food|tomas-vibe|misha|yulya|nasik]

## Что передавать агентам
Каждому агенту в задаче передавать:
- blogger: [имя блогера]
- platform: [платформа]
- job_id: [уникальный id задачи]
- путь к папке задачи
