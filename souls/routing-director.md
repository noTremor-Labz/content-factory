# Роутинг агентов по блогерам и каналам

## tomas-food
- platform: tg
- pipeline: quill, lens, pixel, launch

## tomas-vibe
- platform: tg
- pipeline: quill, lens, pixel, launch

## misha
- platform: yt
- pipeline: quill, lens, pixel, launch

## yulya
- platform: ig
- pipeline: quill, lens, pixel, launch

## nasik
- platform: tt
- pipeline: quill, lens, pixel, launch

## Формат задачи для Director'а
тема: [тема] | платформа: [tg|yt|ig|tt] | формат: пост | блогер: [tomas-food|tomas-vibe|misha|yulya|nasik]

## Что передавать агентам
Каждому агенту в задаче передавать:
- blogger: [имя блогера]
- platform: [платформа]
- job_id: [уникальный id задачи]
- путь к папке задачи
