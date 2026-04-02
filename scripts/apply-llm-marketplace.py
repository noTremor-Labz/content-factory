#!/usr/bin/env python3
"""
Заменяет id моделей OpenClaw во всех зарегистрированных файлах репозитория (и опционально ~/.openclaw)
согласно LLM_MARKETPLACE, config/llm-model-registry.json и выбору слота (primary / alternatives).

Канонические имена — в registry["canonical"]. Для каждой роли (kimi, minimax) в маркетплейсе заданы
primary + alternatives — взаимозаменяемые варианты, если у провайдера нет основной модели.

Переменные окружения:
  LLM_MARKETPLACE     — openrouter | commonstack | together
  LLM_KIMI_SLOT       — индекс слота для роли kimi (0 = primary, 1 = первый alternative, …)
  LLM_MINIMAX_SLOT   — то же для minimax
  LLM_KIMI_PICK       — опционально: подстрока id модели (например mimo-v2-pro, kimi-k2.5); переопределяет SLOT
  LLM_MINIMAX_PICK    — то же для minimax

Примеры:
  LLM_MARKETPLACE=openrouter LLM_KIMI_SLOT=1 python3 scripts/apply-llm-marketplace.py
  LLM_KIMI_PICK=mimo-v2-pro python3 scripts/apply-llm-marketplace.py
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


def role_slots(entry: str | dict) -> list[str]:
    """Список полных id OpenClaw для роли: [primary, ...alternatives]."""
    if isinstance(entry, str):
        return [entry]
    primary = entry.get("primary")
    if not primary:
        raise SystemExit(f"В registry для роли нет primary: {entry!r}")
    alts = entry.get("alternatives") or []
    return [primary] + [a for a in alts if a]


def all_known_strings_for_role(markets: dict, role: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in markets.values():
        entry = m.get(role)
        if entry is None:
            continue
        for s in role_slots(entry):
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def pick_index(slots: list[str], slot_env: str, pick_env: str | None, role: str) -> tuple[int, list[str]]:
    """Возвращает индекс и список предупреждений."""
    warns: list[str] = []
    if pick_env:
        needle = pick_env.strip().lower()
        for i, s in enumerate(slots):
            if needle in s.lower():
                return i, warns
        warns.append(f"{role}: LLM_*_PICK={pick_env!r} не найден среди слотов {slots}; используется primary")
        return 0, warns
    try:
        idx = int(os.environ.get(slot_env, "0").strip() or "0")
    except ValueError:
        warns.append(f"{role}: неверный {slot_env}, используется 0")
        idx = 0
    if idx < 0 or idx >= len(slots):
        warns.append(
            f"{role}: слот {idx} вне диапазона 0..{len(slots) - 1} ({len(slots)} вариантов); используется {min(idx, len(slots) - 1) if slots else 0}"
        )
        idx = max(0, min(idx, len(slots) - 1)) if slots else 0
    return idx, warns


def resolve_target(markets: dict, mp: str, role: str, slot_env: str, pick_env: str | None) -> tuple[str, list[str]]:
    entry = markets[mp][role]
    slots = role_slots(entry)
    idx, warns = pick_index(slots, slot_env, pick_env, role)
    return slots[idx], warns


def migrate_text(
    text: str,
    t_kimi: str,
    t_minimax: str,
    all_kimi: list[str],
    all_minimax: list[str],
) -> tuple[str, int]:
    new = text
    n = 0
    for old in all_kimi:
        if old != t_kimi:
            c = new.count(old)
            if c:
                new = new.replace(old, t_kimi)
                n += c
    for old in all_minimax:
        if old != t_minimax:
            c = new.count(old)
            if c:
                new = new.replace(old, t_minimax)
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

    pick_kimi = os.environ.get("LLM_KIMI_PICK", "").strip() or None
    pick_minimax = os.environ.get("LLM_MINIMAX_PICK", "").strip() or None
    t_kimi, w1 = resolve_target(markets, target_mp, "kimi", "LLM_KIMI_SLOT", pick_kimi)
    t_minimax, w2 = resolve_target(markets, target_mp, "minimax", "LLM_MINIMAX_SLOT", pick_minimax)
    resolve_warns = w1 + w2

    all_kimi = all_known_strings_for_role(markets, "kimi")
    all_minimax = all_known_strings_for_role(markets, "minimax")

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
        new, n = migrate_text(raw, t_kimi, t_minimax, all_kimi, all_minimax)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"[ok] {rel_display(path, root)} — замен: {n}")
            total_repl += n
        else:
            print(f"[--] {rel_display(path, root)} — без изменений")

    print()
    print(f"LLM_MARKETPLACE={target_mp}")
    print(f"  kimi (OpenClaw):    {t_kimi}")
    print(f"  minimax (OpenClaw): {t_minimax}")
    print(f"  canonical.kimi:     {reg['canonical']['kimi']}")
    print(f"  canonical.minimax:  {reg['canonical']['minimax']}")
    k_slots = role_slots(markets[target_mp]["kimi"])
    m_slots = role_slots(markets[target_mp]["minimax"])
    print(f"  слоты kimi в этом маркетплейсе:    {k_slots}")
    print(f"  слоты minimax в этом маркетплейсе: {m_slots}")
    if resolve_warns:
        print()
        for w in resolve_warns:
            print(f"⚠️  {w}", file=sys.stderr)
    if total_repl == 0:
        print("(строки уже соответствуют выбранным маркетплейсу и слотам)")


if __name__ == "__main__":
    main()
