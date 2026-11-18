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

## Три роли: программист, арабист, тестировщик

Подготовлены профили в [.github/agents](.github/agents), единый
[протокол передачи задач](docs/AGENT_PROTOCOL.md) и
[инструкция запуска в ChatGPT Work](docs/CHATGPT_WORK_START.md).

Это конфигурация, **не** три уже работающих автономных процесса.
Поддерживаемые GitHub Copilot custom agents могут использовать профили
`.agent.md`; для ChatGPT Work надо явно открыть инструкции и
уполномоченные репозитории. Для разработки/запуска команд применяйте Codex.
Изменения делаются в отдельных ветках и проходят review, без auto-merge.

## Cloud agent (пилот, по умолчанию выключен)

Подготовлен [ежедневный исполнитель GitHub Actions](.github/workflows/cloud-agent.yml),
[инструкция подключения с телефона](docs/CLOUD_AUTOMATION.md) и
[тестовая задача №4](https://github.com/Xalidmuslim/AI-Council/issues/4).
Пилот формирует черновики и независимую проверку, не изменяет код и
не расходует API без явного включения. Полный автономный выпуск APK,
массовые переводы и генерация изображений пока не подключены.


## Codex Cloud без отдельного API — новая схема

Добавлен [порядок работы Codex + GitHub Actions](docs/CODEX_NO_API_WORKFLOW.md):
первый агент разрабатывает в разрешённом репозитории, GitHub Actions
выполняет настоящие тесты, отдельная задача Codex проверяет diff и логи,
владелец решает вопрос слияния.

Проверяемый генератор инструкций:
`python3 tools/codex_handoff.py` для публичной Issue №48 в
`Arabic-Academy-Flutter`. Он создаёт задания
`programmer.md` / `reviewer.md`, не расходует API и не запускает модели.

**Ограничение:** Codex Cloud нужно отдельно подключить к GitHub в аккаунте;
одни инструкции `AGENTS.md` не запускают модели автоматически. Без
фактических двух задач Codex и результата CI нельзя утверждать, что
самостоятельный программист и проверяющий уже отработали.
