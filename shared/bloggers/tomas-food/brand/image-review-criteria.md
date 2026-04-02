# Критерии ревью промпта и картинки — tomas-food

Документ для Lens: `mode: prompt_review` и `mode: image_review`. Согласуй с `visual-tg.md` и `visual-food.md`.

## Prompt review (`image_prompt.txt`)

1. **Стиль:** Fallout Vault Boy, atompunk, vintage poster, bold outlines, cel-shading; палитра **dusty yellow / sepia-amber** (не matrix green — это vibe-канал).
2. **Сюжет:** есть конкретная сцена с Vault Boy на английском, согласованная с **`post_summary.txt`** (суть поста).
3. **Шаблон:** позитивная часть включает формулировки уровня `Fallout Vault Boy retro atompunk illustration`, `no text`, `square 1:1`.
4. **Негатив:** явный блок `Negative:` — без противоречий (не запрещать мультяшность Vault Boy; запрещать watermark, text, photorealistic stock).
5. **Запреты:** нет текста/логотипов на кадре, нет случайного «чистого» lifestyle food без Vault Boy.

**REJECT**, если палитра перепутана с vibe-каналом, нет Vault Boy, сцена не читается из смысла поста или промпт непереводим в гайд.

## Image review (URL из `ready.md`)

1. **Палитра:** sepia-amber / dusty yellow, без доминирования неонового зелёного (это vibe).
2. **Жанр:** иллюстрация Vault Boy, не фотореалистичный stock.
3. **Качество:** читаемость в превью Telegram, нет лишнего текста на изображении.
4. **Соответствие** промпту и смыслу поста.

**REJECT** при нарушении бренда, слабом качестве или явном несоответствии промпту.
