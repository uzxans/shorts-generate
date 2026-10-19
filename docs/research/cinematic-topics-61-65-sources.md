# Источники для cinematic-тем 61–65

Дата проверки: 9 сентября 2026 года. Использованы официальная документация проектов, стандарт WHATWG и справочные страницы MDN/Chrome for Developers.

## 61 — React `use()` и Suspense

- [React: `use`](https://react.dev/reference/react/use) — `use` читает Promise во время рендера; ожидающий Promise активирует ближайший Suspense; Promise должен быть кэширован или стабилен; rejected Promise передаётся ближайшему Error Boundary.
- [React: `<Suspense>`](https://react.dev/reference/react/Suspense) — чтение Promise через `use` является поддерживаемым источником suspension.

Сценарий не обещает автоматически устранить любой waterfall: он показывает, что заранее созданный Promise избегает позднего старта конкретного запроса из `useEffect`.

## 62 — UUIDv7 в Node.js

- [Node.js 24.16 Crypto API](https://nodejs.org/download/release/v24.16.0/docs/api/crypto.html) — `crypto.randomUUIDv7()` добавлен в 24.16.0; UUID содержит Unix timestamp миллисекундной точности в старших 48 битах и случайные биты; часы немонотонны, строгий рост не гарантируется.
- [Node.js 24.16.0 LTS release](https://nodejs.org/uk/blog/release/v24.16.0) — подтверждает добавление `randomUUIDv7()` в LTS-релиз.

В сценарии локальность B-tree сформулирована как ожидаемое расположение свежих ключей рядом, а не как гарантированное ускорение любой базы данных.

## 63 — Navigation API

- [WHATWG HTML: Navigation API](https://html.spec.whatwg.org/dev/nav-history-apis.html) — событие `navigate`, `navigationType`, `canIntercept`, `intercept()`, исключения для download/hash/cross-origin и передача `event.signal` в асинхронную загрузку.
- [MDN: Navigation API](https://developer.mozilla.org/en-US/docs/Web/API/Navigation_API) — статус Baseline 2026 и назначение API для управления SPA-навигацией.
- [MDN: `NavigateEvent.signal`](https://developer.mozilla.org/en-US/docs/Web/API/NavigateEvent/signal) — сигнал отменяется при отмене перехода, в том числе когда начинается следующая навигация.

## 64 — TypeScript 6

- [TypeScript: Announcing TypeScript 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/) — подтверждает defaults `strict: true`, `module: esnext`, современный `target`, `types: []`, новый `rootDir` и рекомендации явно перечислять пакеты типов.
- [TypeScript: Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/) — подтверждает переход к нативной линии TypeScript 7 и возможность совместного использования с 6.0.

## 65 — CSS `@starting-style`

- [MDN: `@starting-style`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40starting-style) — правило задаёт стартовое состояние для entry transition; примеры для popover и связь с `display ... allow-discrete`.
- [Chrome for Developers: entry and exit animations](https://developer.chrome.com/blog/entry-exit-animations) — объясняет необходимость `allow-discrete` для дискретных свойств и роль `@starting-style` как состояния до открытия.

`prefers-reduced-motion` в сценарии используется как требование доступности, а не как часть механизма `@starting-style`.
