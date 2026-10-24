# AI-Council — автоматический выбор навыков

В этом репозитории установлены 11 навыков **Replica Skill** и `ai-council-router`: автономного ввода команд `/replica-*` больше не требуется **в поддерживаемой среде агента, открывшего этот проект**.

- В Codex: инструкции `AGENTS.md` и навыки в `.agents/skills/`.
- В Claude Code: инструкции `CLAUDE.md` и навыки в `.claude/skills/`.
- При исправлении ошибки выбираются recon, test, targeted build и diff; при редизайне — recon/design/diff; при лаге — анализ и измерение реальных кадров на Android.
- `ANDROID_PLAYBOOK.md` запрещает без причины менять Kotlin/Jetpack Compose или Flutter, удалять данные, книги, перевод, ранее принятый дизайн и оптимизации.
- Навыки автоматически подбираются **только в средах, способных читать файлы этого проекта**. Они не устанавливаются в ChatGPT и другие репозитории автоматически.

## Список 11 навыков

`replica-recon`, `replica-architect`, `replica-design`, `replica-build`, `replica-backend`, `replica-test`, `replica-diff`, `replica-entrepreneur`, `replica-brand`, `replica-launch`, `replica-deploy`.

## Проверка

```bash
python3 -m unittest discover -s tests -v
```

Результаты CI проверяют инструкции/утилиты. Они не доказывают производительность реального Android-приложения.

## Лицензия и источник

Набор адаптирован из [Jakeschincariol/replica-skill](https://github.com/Jakeschincariol/replica-skill), коммит `77c9436fb3d18c3d58169efb8caf4fe906b0dc51`, лицензия MIT. См. `THIRD_PARTY_NOTICES.md` и `LICENSE-REPLICA-SKILL`.

Для других приложений на GitHub навыки надо импортировать в каждый репозиторий или установить глобально в локальной среде агента: файлы AI-Council не включают себя во всех других проектах.
