# Agent dev stack

Оркестрированная разработка в Claude Code. Процесс программирования ведут скиллы Matt Pocock, исполнителей по профилям запускает Paseo, оркестратор — Opus 5.5.

## Стек

| Утилита | Для чего |
| :-- | :-- |
| [RTK](https://github.com/rtk-ai/rtk) | Сжимает вывод команд (git, тесты, сборка). Хук на Bash, для агента прозрачен. Экономия: `rtk gain` |
| [Matt Pocock skills](https://github.com/mattpocock/skills) | Процесс: `grill-me`, `wayfinder`, `to-spec`, `to-tickets`, `implement-spec`, `tdd`, `diagnosing-bugs`, `code-review`, `triage` |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Минимум кода без лишних абстракций, `/ponytail-review` |
| [Playwright CLI](https://playwright.dev/agent-cli/installation) | Браузер для e2e, скриншотов и UI. Снапшоты пишутся в файлы, а не в контекст |
| [CodeGraph](https://github.com/colbymchenry/codegraph) | Граф кода через MCP. Каждый новый worktree индексируется автоматически |
| [Paseo](https://paseo.sh) | Транспорт: worktree, запуск исполнителей по профилям, связь с ними |

Отказались от Superpowers, OpenSpec, GSD, Context Mode и codebase-memory-mcp: они пересекаются со стеком выше.

## Как пользоваться

Скажите оркестратору словами, что нужно. Скилл `orchestrate` сам выберет поток:

| Просьба | Поток |
| :-- | :-- |
| Большая фича | `grill-me` → `to-spec` → `to-tickets` → **согласование** → `implement-spec` |
| Огромная или туманная цель | `wayfinder` → как выше |
| Рефакторинг | `improve-codebase-architecture` → тикеты → **согласование** → исполнитель heavy |
| Небольшая правка | один тикет → **согласование** → исполнитель по сложности |
| Баг | `diagnosing-bugs` → тикет на фикс → **согласование** → исполнитель |
| Ревью | `code-review` + `/ponytail-review` |
| «Как устроено X» в коде | `code-research` (Sonnet) |
| Исследование в интернете | `web-research` (Gemini) |
| Картинки или UI-ассеты | `images` (Codex) |

Исполнители работают только над тикетами с меткой `ready-for-agent`. Эту метку оркестратор ставит после вашего явного «да».

## Маршрутизация (профили Paseo)

| Профиль | Модель | Мышление | Задачи |
| :-- | :-- | :-- | :-- |
| `orchestrator` | Opus 5.5 | medium | Оркестрация |
| `implementer-heavy` | Opus 5.5 | medium | Рефакторинг, обширные изменения, API, миграции |
| `implementer-medium` | Sonnet 5.5 | medium | Типовые фичи и багфиксы, UI-код |
| `implementer-light` | Haiku 5.5 | medium | Лёгкие правки, до ~3 файлов |
| `implementer-trivial` | Haiku 5.5 | low | Переименования, бойлерплейт, тексты |
| `merger` | Haiku 5.5 | medium | Вливание тикетов в integration-ветку |
| `reviewer` | Sonnet 5.5 | medium | Оси Standards и Spec в `code-review` |
| `code-research` | Sonnet 5.5 | medium | Исследование кода |
| `web-research` | Gemini 3.8 Flash (Antigravity) | high | Исследование в интернете |
| `images` | GPT-6-Luna (Codex) | medium | Картинки, PNG на прозрачном фоне |
| `advisor` | GPT-6-Luna (Codex) | medium | Второе мнение по архитектуре |
| `arbiter` | Fable 5.1 | medium | Спорные замечания и неразрешённые споры |

Код пишут только модели Claude. Одновременно работают не больше 3 агентов, пишущих код.

## Git и ревью

- Для каждой спеки создаётся `integration/<spec>` от `origin/dev`, для каждого тикета — свой worktree `ticket/<N>-<slug>`. Тикеты вливаются в integration-ветку, затем один PR в `dev` через merge commit. В `main` — только при релизе.
- Тикеты закрываются сразу после merge в dev. Ни TODO.md, ни метки `in-dev` нет.
- Конвейер ревью: тесты → `/ponytail-review` у исполнителя → `code-review` в конце спеки. При конфликте замечаний действует приоритет: тесты > спека/тикет > Ponytail > advisor/arbiter. Повторный спор решает `arbiter`, неразрешённый — вы.

## Установка

Нужны `git`, `python3`, `node`/`npm`, Claude Code и `gh` (с авторизацией). Paseo ставится заранее.

```bash
git clone git@github.com:<you>/agent-dev-stack.git
cd agent-dev-stack
./install.sh
paseo daemon restart
claude   # новая сессия
```

Установщик можно запускать повторно. Что он делает:
1. Ставит RTK, CodeGraph, Playwright CLI с Chromium и плагины Ponytail и Pocock.
2. Копирует скиллы `orchestrate` и `pocock-paseo` и хук автоиндексации CodeGraph в `~/.claude/`.
3. Добавляет в `~/.claude/settings.json` хуки RTK и CodeGraph, deny-правила для опасных git-команд и `PONYTAIL_DEFAULT_MODE=full`. Старый файл сохраняется в `~/.claude/backups/`.
4. Вписывает блок правил между маркерами `DEV_STACK` в `~/.claude/CLAUDE.md`. Остальное содержимое файла не трогает.
5. Добавляет `.codegraph/` в глобальный gitignore.
6. Копирует встроенные скиллы Paseo (`paseo`, `paseo-advisor`, `paseo-committee`, `paseo-handoff`, `paseo-help`, `paseo-plugin`), но только те, которых ещё нет. Свои скиллы Paseo обновляет сам.
7. Настраивает Paseo в `~/.paseo/config.json` (бэкап сохраняется рядом): MCP внутри агентов включён, browser tools выключены, автоархивация после merge включена, Antigravity включён, OpenCode, Pi и Muse выключены, диктовка через локальный whisper-turbo, голосовой режим выключен. Профили с теми же `id` заменяются. Адрес, CORS, relay и ключи не трогаются.
8. Ставит плагины Paseo из `paseo/plugins.txt`: better-paseo, prompt-manager, resources, shell-yeah, usage-auto-resume.

Если нужно только обновить конфиги без загрузок: `SKIP_INSTALL=1 ./install.sh`.

В каждом репозитории один раз скажите оркестратору «настрой репо для оркестрации». Он вместе с вами пройдёт `setup-matt-pocock-skills`: трекер GitHub и метки triage.

## Структура

```
install.sh                         установщик
claude/CLAUDE.dev-stack.md         блок правил для ~/.claude/CLAUDE.md
claude/hooks/codegraph-autoindex.sh  SessionStart: индекс CodeGraph в каждом worktree
claude/skills/orchestrate/         точка входа: просьба словами → поток Pocock
claude/skills/pocock-paseo/        роли Pocock → агенты Paseo по профилям
paseo/agent-profiles.json          профили исполнителей
paseo/settings.json                переносимые настройки Paseo (без адресов и ключей)
paseo/plugins.txt                  плагины Paseo (id в реестре plugins.paseo.sh)
paseo/skills/                      встроенные скиллы Paseo (снимок)
```

## Проверенные версии

Стек проверен 2026-11-01 только на этих версиях:

| Компонент | Версия |
| :-- | :-- |
| Claude Code | 2.1.316 |
| Paseo | 0.14.0 |
| Node | v26.13.0 |
| RTK | 1.1.0 |
| CodeGraph | 1.6.2 |
| @playwright/cli | 0.1.23 |
| Плагин ponytail | 5.3.3 |
| Плагин mattpocock-skills | 1.3.1 |
| Плагины Paseo | better-paseo `f7dcded`, prompt-manager `74d00ca`, resources `e3ecb0b`, shell-yeah 1.3.1, usage-auto-resume `b115098` |

`install.sh` ставит **последние** версии. На более новых стек не проверялся. Установщик показывает предупреждение в начале и список установленных версий в конце. Если версии отличаются, проверьте, что `orchestrate` находит скиллы Pocock по именам и что хуки срабатывают.

## Ограничения

- Исполнители Claude работают в режиме `auto`. Если классификатор заблокирует действие, агент ждёт решения оркестратора. Deny-правила действуют и в `bypassPermissions`.
- Deny-правила сопоставляют начало команды. Для надёжности включите защиту веток `main` и `dev` на GitHub.
- Агенты Gemini и Codex работают без RTK, Ponytail и deny-правил, поэтому код им не доверяется.
- Скиллы Pocock, которые вызываются только слэшем, оркестратор читает из файлов плагина. Если Pocock переименует скилл, поправьте таблицу в `orchestrate`.
- CodeGraph отправляет анонимную статистику. Отключение: `codegraph telemetry off`.
