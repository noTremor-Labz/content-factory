# Роутинг агентов по блогерам и каналам

## tomas
- food: quill-tomas-tg-food, lens-tomas-tg-food, pixel, launch-tomas-tg-food
- vibe: quill-tomas-tg-vibe, lens-tomas-tg-vibe, pixel, launch-tomas-tg-vibe

## misha
- yt: quill-misha-yt, lens-misha-yt, pixel, launch-misha-yt

## yulya
- ig: quill-yulya-ig, lens-yulya-ig, pixel, launch-yulya-ig

## nasik
- tt: quill-nasik-tt, lens-nasik-tt, pixel, launch-nasik-tt

## Формат задачи
тема: [тема] | платформа: [telegram|youtube-shorts|instagram-reels|tiktok] | формат: пост | блогер: [tomas|misha|yulya|nasik] | канал: [food|vibe|yt|ig|tt]

## Примечания
- pixel — универсальный агент, один для всех блоггеров и площадок
- pixel читает визуальный бренд из /home/node/shared/bloggers/{блогер}/brand/
- pixel читает правила площадки из /home/node/shared/platform-specs/{платформа}.md
- Все поля формата задачи обязательны для корректной работы pixel
