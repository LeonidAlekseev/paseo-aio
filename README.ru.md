# Paseo AIO

**Версия для Codex:** отдельный установщик, 12 профилей, навыки и нативные хуки.
См. [установку под Codex](README.codex.ru.md). Ниже описан исходный вариант для
Claude; для Codex нужен `install-codex.sh`, а не `install.sh`.

[🇬🇧 English](README.md) | **🇷🇺 Русский**

[![Claude Code](https://img.shields.io/badge/Claude%20Code-2.1.316-d97757)](https://claude.com/claude-code)
[![Paseo](https://img.shields.io/badge/Paseo-0.14.0-black)](https://paseo.sh)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)](#проверенные-версии)
[![Shell](https://img.shields.io/badge/install-bash-4EAA25?logo=gnubash&logoColor=white)](install.sh)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Оркестрированная разработка в Claude Code, которая ставится одной командой. Процесс ведут скиллы Matt Pocock. Paseo
запускает исполнителей по профилям моделей. Оркестратор на Opus 5.5 планирует работу, раздаёт тикеты и вливает
результат в `dev`.

> [!WARNING]
> `install.sh` ставит **последние** версии всех инструментов, а стек проверен только на версиях из раздела
> [Проверенные версии](#проверенные-версии). На более новых он не проверялся. Установщик выводит предупреждение в начале
> и список установленных версий в конце, чтобы их можно было сравнить.

## Оглавление

- [Обзор](#обзор)
- [Возможности](#возможности)
- [Стек](#стек)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [Использование](#использование)
- [Маршрутизация моделей](#маршрутизация-моделей)
- [Как это работает](#как-это-работает)
- [Git и ревью](#git-и-ревью)
- [Безопасность](#безопасность)
- [Проверенные версии](#проверенные-версии)
- [Решение проблем](#решение-проблем)
- [Частые вопросы](#частые-вопросы)
- [Структура](#структура)
- [Благодарности](#благодарности)
- [Лицензия](#лицензия)

## Обзор

Вы описываете задачу словами: «сделай фичу X», «отрефактори модуль Y», «найди баг», «исследуй, как устроено Z». Скилл
`orchestrate` выбирает подходящий поток Pocock: допрос по плану, спека, тикеты и реализация. Затем он останавливается и
ждёт вашего согласия. После согласия на каждый тикет запускается свой агент Paseo в отдельном worktree. Модель
подбирается по сложности тикета. В конце оркестратор проверяет результат и вливает его в `dev` через merge commit.

У каждой задачи ровно один владелец. Процессом управляет Pocock, транспортом и worktree — Paseo, объёмом кода —
Ponytail, навигацией по коду — CodeGraph, сжатием вывода — RTK. Поэтому два инструмента никогда не берутся за одну и ту
же работу.

## Возможности

- 🗣️ **Задачи словами**: просто попросите. Слэш-команды тоже работают.
- 🧭 **Процесс Pocock**: `grill-me` → `to-spec` → `to-tickets` → `implement-spec`, для огромных целей — `wayfinder`.
- 🚦 **Гейт согласования**: исполнители берут только тикеты с меткой `ready-for-agent`, а её ставят только после вашего
  явного «да».
- 🤖 **Маршрутизация моделей**: 12 профилей Paseo, у каждого типа задач своя модель и уровень мышления.
- 🌳 **Worktree на тикет**: integration-ветка на спеку, тикеты вливаются в неё, затем один PR в `dev`.
- 🧠 **CodeGraph в каждом worktree**: хук SessionStart копирует индекс из основного checkout и досинхронизирует его.
- ✂️ **Ponytail**: минимум кода и `/ponytail-review` перед сдачей работы.
- 📉 **RTK**: сжатый вывод команд экономит контекст.
- 🛡️ **Deny-правила git**: запрещены force push, push в `main`, `reset --hard`, `clean -f` и похожие команды.
- 🔁 **Повторный запуск установщика безопасен**: он сохраняет ваш `CLAUDE.md`, другие профили и уже установленные
  скиллы Paseo, а конфиги перед изменением копирует в бэкап.

## Стек

| Инструмент                                                     | Роль                                                                                    |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [Matt Pocock skills](https://github.com/mattpocock/skills)     | Процесс: спека, тикеты, TDD, диагностика багов, код-ревью, triage                       |
| [Paseo](https://paseo.sh)                                      | Транспорт: worktree, исполнители по профилям, вопросы и ответы, архивация               |
| [Ponytail](https://github.com/DietrichGebert/ponytail)         | Минимальный рабочий код, `/ponytail-review`                                             |
| [CodeGraph](https://github.com/colbymchenry/codegraph)         | Граф кода через MCP, автоиндекс в каждом worktree                                       |
| [RTK](https://github.com/rtk-ai/rtk)                           | Сжимает вывод команд (git, тесты, сборка)                                               |
| [Playwright CLI](https://playwright.dev/agent-cli/installation) | Браузер для e2e, скриншотов и UI. Снапшоты пишутся в файлы, а не в контекст            |

Не используются, потому что пересекаются со стеком выше: Superpowers, OpenSpec, GSD, Context Mode, codebase-memory-mcp.

## Установка

### Что нужно заранее

- **git**, **python3**, **node** + **npm**, **[gh](https://cli.github.com)** с авторизацией;
- **[Claude Code](https://claude.com/claude-code)**;
- **[Paseo](https://paseo.sh)** с подключёнными провайдерами Claude, Codex и Antigravity.

### Установка

```sh
git clone git@github.com:LeonidAlekseev/paseo-aio.git
cd paseo-aio
./install.sh
paseo daemon restart
claude                      # новая сессия, чтобы подхватились хуки и MCP
```

Обновить только конфиги, без загрузок:

```sh
SKIP_INSTALL=1 ./install.sh
```

Что делает установщик:

1. Ставит RTK, CodeGraph, Playwright CLI с Chromium и плагины Ponytail и Matt Pocock skills.
2. Копирует скиллы `orchestrate` и `pocock-paseo` и хук автоиндекса CodeGraph в `~/.claude/`.
3. Добавляет в `~/.claude/settings.json` хуки RTK и CodeGraph, deny-правила git и `PONYTAIL_DEFAULT_MODE=full`. Старый
   файл сохраняет в `~/.claude/backups/`.
4. Вписывает блок правил между маркерами `DEV_STACK` в `~/.claude/CLAUDE.md`. Остальной файл не трогает.
5. Добавляет `.codegraph/` в глобальный gitignore.
6. Копирует встроенные скиллы Paseo, но только недостающие: свои скиллы Paseo обновляет сам.
7. Сливает настройки и профили Paseo в `~/.paseo/config.json` (с бэкапом) и ставит плагины Paseo из
   `paseo/plugins.txt`.

### Какие настройки Paseo применяются

| Настройка                    | Значение                                                               |
| ---------------------------- | ---------------------------------------------------------------------- |
| Плагины                      | better-paseo, prompt-manager, resources, shell-yeah, usage-auto-resume |
| MCP внутри агентов           | включён                                                                |
| Browser tools                | выключены, браузер — это Playwright CLI                                |
| Автоархивация после merge    | включена                                                               |
| Провайдеры                   | Antigravity включён, OpenCode, Pi и Muse выключены                     |
| Профили агентов              | 12, см. [Маршрутизация моделей](#маршрутизация-моделей)                |

Адрес демона, CORS, relay и ключи установщик не трогает.

### Опциональные настройки

Установщик их не применяет. Если нужны, включите вручную:

- **Тема Pure Black**: выберите её в настройках приложения Paseo. Тема хранится в приложении, а не в демоне.
- **Диктовка через локальный Whisper**: в настройках приложения Paseo включите диктовку с локальной моделью
  `whisper-turbo`.

### В каждом репозитории

Один раз скажите оркестратору «настрой репо для оркестрации». Вместе с вами он пройдёт `setup-matt-pocock-skills`:
трекер GitHub и метки triage.

## Быстрый старт

```text
Вы:    Добавь экспорт в CSV на страницу отчётов.
Агент: grill-me → спека #41 → тикеты #42–#45

       тикет | цель            | сложность → профиль         | блокируется
       #42   | сервис экспорта | средняя → implementer-medium | —
       #43   | CSV-форматтер   | лёгкая  → implementer-light  | —
       #44   | кнопка и роут   | средняя → implementer-medium | #42 #43
       #45   | e2e-тест        | лёгкая  → implementer-light  | #44

       Согласовать?
Вы:    Да.
Агент: integration/csv-export ← #42 #43 (параллельно) → #44 → #45 → code-review → PR #46 → dev
```

## Использование

Просите словами. `orchestrate` сам подберёт поток:

| Просьба                          | Поток                                                                              |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| Большая фича                     | `grill-me` → `to-spec` → `to-tickets` → **согласование** → `implement-spec`        |
| Огромная или туманная цель       | `wayfinder` → затем как выше                                                       |
| Рефакторинг                      | `improve-codebase-architecture` → тикеты → **согласование** → `implementer-heavy`  |
| Небольшая правка                 | один тикет → **согласование** → один исполнитель, PR сразу в `dev`                 |
| Баг                              | `diagnosing-bugs` → тикет на фикс → **согласование** → исполнитель                 |
| Ревью                            | `code-review` + `/ponytail-review`                                                 |
| «Как устроено X» в коде          | профиль `code-research` (Sonnet)                                                   |
| Исследование, нужен интернет     | профиль `web-research` (Gemini)                                                    |
| Картинки или UI-ассеты           | профиль `images` (Codex)                                                           |
| Разобрать issues                 | `triage`                                                                           |
| Релиз                            | PR `dev` → `main` после вашего согласия                                            |

Слэш-команды (`/to-spec`, `/grill-me`, `/wayfinder` и другие) выполняются как есть.

## Маршрутизация моделей

| Профиль               | Модель                         | Мышление | Задачи                                                      |
| --------------------- | ------------------------------ | :------: | ----------------------------------------------------------- |
| `orchestrator`        | Opus 5.5                       |  medium  | Планирование, маршрутизация, ответы исполнителям, merge     |
| `implementer-heavy`   | Opus 5.5                       |  medium  | Рефакторинг, обширные изменения, миграции, публичный API    |
| `implementer-medium`  | Sonnet 5.5                     |  medium  | Типовые фичи и багфиксы, UI-код, фиксы по ревью             |
| `implementer-light`   | Haiku 5.5                      |  medium  | Лёгкие правки, до ~3 файлов                                 |
| `implementer-trivial` | Haiku 5.5                      |   low    | Переименования, бойлерплейт, тексты                         |
| `merger`              | Haiku 5.5                      |  medium  | Вливание тикетов в integration-ветку                        |
| `reviewer`            | Sonnet 5.5                     |  medium  | Оси Standards и Spec в `code-review`                        |
| `code-research`       | Sonnet 5.5                     |  medium  | Исследование кода                                           |
| `web-research`        | Gemini 3.8 Flash (Antigravity) |   high   | Исследование в интернете                                    |
| `images`              | GPT-6-Luna (Codex)             |  medium  | Картинки, PNG на прозрачном фоне                            |
| `advisor`             | GPT-6-Luna (Codex)             |  medium  | Второе мнение по архитектуре (другое семейство моделей)     |
| `arbiter`             | Fable 5.1                      |  medium  | Спорные замечания и неразрешённые споры                     |

Код пишут только модели Claude. Одновременно работают не больше 3 агентов, пишущих код.

## Как это работает

1. **🗣️ Просьба**: `orchestrate` определяет её тип и выбирает поток.
2. **🔧 Подготовка**: `git fetch`, проверка, что есть `dev`, поиск уже идущей работы (открытые PR, агенты Paseo), чтобы
   её не дублировать.
3. **📝 План**: Pocock допрашивает вас по плану, пишет спеку и разбивает её на тикеты с блокировками. Всё это живёт в
   GitHub issues.
4. **✋ Согласование**: оркестратор показывает план таблицей и останавливается. Согласованные тикеты получают метку
   `ready-for-agent`.
5. **🌳 Worktree**: `integration/<spec>` от свежего `origin/dev` и worktree `ticket/<N>-<slug>` на каждый тикет. Всё
   создаётся через Paseo. CodeGraph индексирует каждый worktree при старте агента.
6. **🤖 Исполнители**: на каждый тикет свой агент с профилем по сложности. Исполнитель работает по `tdd`, прогоняет
   проверки и `/ponytail-review`, вливает к себе свежую integration-ветку и отчитывается. С вопросами он обращается к
   оркестратору, а тот отвечает сам или спрашивает вас.
7. **🔀 Merge**: агент `merger` вливает каждый готовый тикет в integration-ветку, и открываются следующие тикеты.
8. **🔍 Ревью**: `code-review` запускает двух агентов `reviewer` (Standards и Spec), затем идёт один раунд исправлений.
9. **🚀 Интеграция**: PR `integration/<spec>` → `dev` через merge commit, тикеты закрываются.
10. **🧹 Очистка**: Paseo архивирует агентов и worktree, локальные ветки и заметки удаляются.

## Git и ревью

- **Ветки**: `integration/<spec>` от `origin/dev`, `ticket/<N>-<slug>` от integration-ветки. Без rebase и force push.
  `main` меняется только при релизе.
- **Issues** закрываются сразу после merge в `dev`. Нет ни TODO-файла, ни метки `in-dev`.
- **Конвейер ревью**: тесты → `/ponytail-review` у исполнителя → `code-review` в конце спеки.
- **Приоритет при конфликте**: тесты > спека/тикет > Ponytail > advisor/arbiter. Один раунд исправлений на каждое
  ревью. Повторный спор решает `arbiter`, неразрешённый — вы.

## Безопасность

- **Гейт согласования**: ничего не реализуется без вашего явного согласия. Молчание — не согласие.
- **Deny-правила git** в `~/.claude/settings.json` запрещают force push, push в `main`, `reset --hard`, `clean -f`,
  `checkout -- .`, `restore .`, удаление `main` и `dev` и `gh repo delete`.
- **Бэкапы**: `settings.json` сохраняется в `~/.claude/backups/`, `config.json` копируется в
  `~/.paseo/config.json.bak-<время>`.
- **Агенты не на Claude** (Gemini, Codex) работают без RTK, Ponytail и deny-правил, поэтому код им не доверяется.
- **Исполнители работают в режиме `auto`**. Если классификатор заблокирует действие, агент ждёт решения оркестратора.

> [!TIP]
> Deny-правила сопоставляют только начало команды. Для надёжности включите защиту веток `main` и `dev` на GitHub.

## Проверенные версии

Стек проверен 2026-11-01 на Linux:

| Компонент                  | Версия                                                                                                          |
| -------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Claude Code                | 2.1.316                                                                                                         |
| Paseo                      | 0.14.0                                                                                                          |
| Node                       | v26.13.0                                                                                                        |
| RTK                        | 1.1.0                                                                                                           |
| CodeGraph                  | 1.6.2                                                                                                           |
| @playwright/cli            | 0.1.23                                                                                                          |
| Плагин ponytail            | 5.3.3                                                                                                           |
| Плагин mattpocock-skills   | 1.3.1                                                                                                           |
| Плагины Paseo              | better-paseo `f7dcded`, prompt-manager `74d00ca`, resources `e3ecb0b`, shell-yeah 1.3.1, usage-auto-resume `b115098` |

> [!CAUTION]
> На более новых версиях стек не проверялся. После обновления убедитесь, что `orchestrate` находит скиллы Pocock по
> именам и что хуки срабатывают.

## Решение проблем

#### Нет `/to-spec`, `/implement-spec` и других скиллов Pocock

Плагин не установлен, или сессия запущена раньше, чем он был установлен. Выполните:

```sh
claude plugin install mattpocock-skills@claude-plugins-official
```

Затем откройте новую сессию `claude`.

#### Установку плагинов блокирует классификатор auto-режима

Выполните команды из шага 1 установщика сами, в терминале вне сессии агента.

#### В worktree нет индекса CodeGraph

Индекс строится в фоне при старте сессии. Проверьте лог:

```sh
tail ~/.claude/hooks/codegraph-autoindex.log
```

#### `list_profiles` возвращает пустой список

Выполните `paseo daemon restart` и проверьте, что в `~/.paseo/config.json` есть `daemon.agentProfiles`.

#### Профиль не запускается: неизвестная модель

ID моделей зависят от ваших провайдеров. Сверьте их с `paseo provider models claude` (или `codex`, `antigravity`) и
поправьте `paseo/agent-profiles.json`.

#### `git push` запрещён

Сработало deny-правило. Force push и push в `main` запрещены намеренно, их выполняете вы сами в терминале.

## Частые вопросы

**Нужно ли вводить слэш-команды?** Нет. Просите словами: `orchestrate` прочитает нужный скилл Pocock, включая те,
которые вызываются только слэшем.

**Почему один PR на спеку, а не на каждый тикет?** Так устроена модель Pocock с integration-веткой. Тикеты вливаются в
одну ветку, и вы ревьюите фичу целиком.

**Можно поменять модели?** Да. Поправьте `paseo/agent-profiles.json` и запустите `SKIP_INSTALL=1 ./install.sh`. Поле
`notes` подсказывает оркестратору, когда брать профиль.

**Установщик перезапишет мой CLAUDE.md?** Нет. Он заменяет только блок между `<!-- DEV_STACK_START -->` и
`<!-- DEV_STACK_END -->`.

**Работает ли на macOS?** Вероятно, но проверялось только на Linux.

## Структура

```
install.sh                           установщик
claude/CLAUDE.dev-stack.md           блок правил для ~/.claude/CLAUDE.md
claude/hooks/codegraph-autoindex.sh  SessionStart: индекс CodeGraph в каждом worktree
claude/skills/orchestrate/           точка входа: просьба словами → поток Pocock
claude/skills/pocock-paseo/          адаптер: роли Pocock → агенты Paseo по профилям
paseo/agent-profiles.json            профили исполнителей
paseo/settings.json                  переносимые настройки Paseo (без адресов и ключей)
paseo/plugins.txt                    плагины Paseo (id в реестре plugins.paseo.sh)
paseo/skills/                        снимок встроенных скиллов Paseo
```

## Благодарности

- [Matt Pocock skills](https://github.com/mattpocock/skills): процесс разработки.
- [Paseo](https://paseo.sh): оркестрация агентов и worktree.
- [Ponytail](https://github.com/DietrichGebert/ponytail), [CodeGraph](https://github.com/colbymchenry/codegraph),
  [RTK](https://github.com/rtk-ai/rtk), [Playwright CLI](https://playwright.dev/agent-cli/installation).
- Плагины Paseo: [better-paseo](https://github.com/RoundRedDot/better-paseo),
  [prompt-manager](https://github.com/yannelli/paseo-prompt-manager),
  [resources](https://github.com/ZedObaia/paseo-plugins),
  [shell-yeah](https://plugins.paseo.sh), [usage-auto-resume](https://github.com/babo-jeonguk/paseo-usage-auto-resume).

## Лицензия

[MIT](LICENSE).

`paseo/skills/` — снимок встроенных скиллов [Paseo](https://github.com/getpaseo/paseo). Лицензия MIT на них не
распространяется: они остаются под Apache License 2.0 от Paseo, см. [paseo/skills/LICENSE](paseo/skills/LICENSE).
