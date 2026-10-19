import unittest
from pathlib import Path

from telegram_bot.settings import BotSettings


class TelegramBotSettingsTest(unittest.TestCase):
    def test_builds_paths_and_admin_ids_from_env(self):
        settings = BotSettings.from_env(
            {
                "TELEGRAM_BOT_TOKEN": "123:token",
                "TELEGRAM_ADMIN_IDS": "10, 20",
                "TELEGRAM_BOT_DB": "state/bot.db",
                "MANUAL_PAYMENT_TEXT": "Переведите 50 рублей на номер +79626957711 Тинькофф.",
                "ALT_PAYMENT_TEXT": "Напишите админу для оплаты из другой страны",
            },
            root=Path("/app"),
        )

        self.assertEqual(settings.telegram_token, "123:token")
        self.assertEqual(settings.manual_payment_text, "Переведите 50 рублей на номер +79626957711 Тинькофф.")
        self.assertEqual(settings.alt_payment_text, "Напишите админу для оплаты из другой страны")
        self.assertEqual(settings.admin_ids, (10, 20))
        self.assertEqual(settings.db_path, Path("/app/state/bot.db"))
        self.assertEqual(settings.input_dir, Path("/app/input/telegram"))
        self.assertEqual(settings.output_dir, Path("/app/output/telegram"))
        self.assertEqual(settings.temp_dir, Path("/app/temp/telegram"))

    def test_rejects_missing_token(self):
        with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
            BotSettings.from_env({}, root=Path("/app"))

    def test_loads_from_env_file(self):
        env_file = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".env")
        try:
            env_file.write_text(
                "TELEGRAM_BOT_TOKEN=test-token\n"
                "TELEGRAM_ADMIN_IDS=7\n"
                "MANUAL_PAYMENT_TEXT=Переведите на Тинькофф\n"
                "ALT_PAYMENT_TEXT=Другой способ\n",
                encoding="utf-8",
            )

            settings = BotSettings.from_env_file(env_file, root=Path("/app"))

            self.assertEqual(settings.telegram_token, "test-token")
            self.assertEqual(settings.admin_ids, (7,))
            self.assertEqual(settings.manual_payment_text, "Переведите на Тинькофф")
            self.assertEqual(settings.alt_payment_text, "Другой способ")
        finally:
            env_file.unlink(missing_ok=True)
