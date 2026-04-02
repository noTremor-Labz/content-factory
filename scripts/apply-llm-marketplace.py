#!/usr/bin/env python3
"""
Заменяет id моделей OpenClaw во всех зарегистрированных файлах репозитория (и опционально ~/.openclaw)
согласно LLM_MARKETPLACE и config/llm-model-registry.json.

Канонические логические имена см. в registry["canonical"] (например moonshotai/kimi-k2.5).
В конфиге OpenClaw используются полные строки вида <маркетплейс>/... из registry["marketplaces"][LLM_MARKETPLACE].

Использование:
  LLM_MARKETPLACE=commonstack python3 scripts/apply-llm-marketplace.py
  LLM_MARKETPLACE=openrouter python3 scripts/apply-llm-marketplace.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_registry(root: Path) -> dict:
    p = root / "config" / "llm-model-registry.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def migrate_text(text: str, target_mp: str, reg: dict) -> tuple[str, int]:
    markets = reg["marketplaces"]
    if target_mp not in markets:
        raise SystemExit(f"Неизвестный LLM_MARKETPLACE={target_mp!r}. Допустимо: {list(markets)}")

    t_kimi = markets[target_mp]["kimi"]
    t_minimax = markets[target_mp]["minimax"]
    new = text
    n = 0
    for mp, m in markets.items():
        if mp == target_mp:
            continue
        for role in ("kimi", "minimax"):
            old = m[role]
            neu = t_kimi if role == "kimi" else t_minimax
            if old != neu:
                c = new.count(old)
                if c:
                    new = new.replace(old, neu)
                    n += c
    return new, n


def rel_display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    target_mp = os.environ.get("LLM_MARKETPLACE", "openrouter").strip().lower()
    if not target_mp:
        target_mp = "openrouter"

    reg = load_registry(root)
    markets = reg["marketplaces"]
    if target_mp not in markets:
        print(f"Ошибка: LLM_MARKETPLACE={target_mp!r} нет в registry. Варианты: {list(markets.keys())}", file=sys.stderr)
        sys.exit(1)

    repo_files = [
        root / "souls" / "director.md",
        root / "openclaw" / "openclaw.json",
        root / "openclaw" / "openclaw-internal.json",
        root / "scripts" / "2-create-agents.sh",
    ]

    oc_home = os.environ.get("OPENCLAW_CONFIG_DIR", "").strip()
    if oc_home:
        wd_tools = Path(oc_home).expanduser() / "workspace-director" / "TOOLS.md"
        if wd_tools.is_file():
            repo_files.append(wd_tools)

    total_repl = 0
    for path in repo_files:
        if not path.is_file():
            print(f"[skip] нет файла: {path}")
            continue
        raw = path.read_text(encoding="utf-8")
        new, n = migrate_text(raw, target_mp, reg)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"[ok] {rel_display(path, root)} — замен: {n}")
            total_repl += n
        else:
            print(f"[--] {rel_display(path, root)} — без изменений")

    t_kimi = markets[target_mp]["kimi"]
    t_minimax = markets[target_mp]["minimax"]
    print()
    print(f"LLM_MARKETPLACE={target_mp}")
    print(f"  kimi (OpenClaw):    {t_kimi}")
    print(f"  minimax (OpenClaw): {t_minimax}")
    print(f"  canonical.kimi:     {reg['canonical']['kimi']}")
    print(f"  canonical.minimax:  {reg['canonical']['minimax']}")
    if total_repl == 0:
        print("(строки уже соответствуют выбранному маркетплейсу)")


if __name__ == "__main__":
    main()
