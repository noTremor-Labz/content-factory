# Роутинг агентов по блогерам и каналам

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
