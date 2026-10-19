---
format: 1080x1920
duration: 58.033s
message: RSC требуют актуальных серверных исправлений.
arc: Hook → Mechanism → Risk → Example → Action → Takeaway
audience: React developers
mode: autonomous
music: original minimal electronic
---
## Video direction
Dark technical editorial canvas with blue data, orange risk and lime remedy. Large Russian typography. Sequential reveals over each scene; hold last 1.2s. Thin grid, depth on server stack, smooth power3 transforms and focused camera attention. No people, chaos or gratuitous decoration.
## Frame 1 — Hook
- duration: 4s
- src: compositions/frames/01-hook.html
- status: animated
- transition_in: cut
- scene: Один запрос — и сервер под угрозой?
0–1s hero question first two words; 1–2s server packet impact; 2–4s question completes.
## Frame 2 — RSC simply
- duration: 10s
- src: compositions/frames/02-rsc.html
- status: animated
- transition_in: slide
- scene: Сервер готовит UI. Браузер добавляет интерактивность.
0–2s title; 2–4.5s server stack; 4.5–7s payload moves to browser; 7–10s client button and summary.
## Frame 3 — Security mechanism
- duration: 10s
- src: compositions/frames/03-risk.html
- status: animated
- transition_in: slide
- scene: Ошибка разбора запроса может открыть выполнение кода на сервере.
0–2s title; 2–4s malicious packet enters parser; 4–7s boundary breaks; 7–10s RCE consequence. Label disclosure December 2025 and CVE-2025-55182.
## Frame 4 — Real application
- duration: 10s
- src: compositions/frames/04-example.html
- status: animated
- transition_in: slide
- scene: Магазин на Next.js App Router. Витрина работает, уязвимая зависимость скрыта.
0–2s Next.js shop title; 2–4.5s product interface; 4.5–7s server dependency revealed below; 7–10s “Работает ≠ защищено”. This is an illustrative vulnerable deployment, not all Next.js apps.
## Frame 5 — Update path
- duration: 12s
- src: compositions/frames/05-update.html
- status: animated
- transition_in: slide
- scene: Проверь зависимости. Обнови фреймворк и RSC-пакеты. Тест → сборка → деплой.
0–3s audit; 3–6s patched supported line; 6–9s test and build; 9–12s deploy turns green. No specific stale version pins.
## Frame 6 — Takeaway
- duration: 8s
- src: compositions/frames/06-end.html
- status: animated
- transition_in: slide
- scene: Патч должен дойти до сервера.
0–2s update package; 2–4s package locks into protected server; 4–8s final message and source react.dev. RSC performance benefit does not replace patch maintenance.

## Frame 7 — Подписка
- duration: 4.033333s
- status: animated
- scene: Supplied frog.mp4 subscription animation, full screen
- voiceover: Подпишись, чтобы не пропустить новые разборы.
- transition_in: cut
54.0–58.033s supplied animation with original music and Russian CTA voice.
