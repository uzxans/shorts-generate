import json
import subprocess
import unittest
from pathlib import Path

from telegram_bot.domain import Plan
from telegram_bot.settings import BotSettings
from telegram_bot.storage import consume_free_daily_credit, create_job, get_job, init_db
from telegram_bot.worker import build_telegram_compress_command, process_next_job, sanitize_error_message


class FakeRun:
    def __init__(self, stdout: str = ""):
        self.stdout = stdout


class RecordingRunner:
    def __init__(self, metadata_duration: int = 42):
        self.commands = []
        self.metadata_duration = metadata_duration

    def __call__(self, cmd):
        self.commands.append(cmd)
        if cmd and cmd[0] == "ffprobe":
            return FakeRun(json.dumps({"format": {"duration": str(self.metadata_duration)}}))
        if "--dump-json" in cmd:
            return FakeRun(json.dumps({"duration": self.metadata_duration}))
        if "after_move:filepath" in cmd:
            return FakeRun("/tmp/downloaded.mp4\n")
        return FakeRun("")


class FailingLocalizeRunner(RecordingRunner):
    def __call__(self, cmd):
        self.commands.append(cmd)
        if "--dump-json" in cmd:
            return FakeRun(json.dumps({"duration": self.metadata_duration}))
        if "after_move:filepath" in cmd:
            return FakeRun("/tmp/downloaded.mp4\n")
        if any("localize_video.py" in part for part in cmd):
            raise RuntimeError("No translated segments to synthesize.")
        return FakeRun("")


class TimeoutLocalizeRunner(RecordingRunner):
    def __call__(self, cmd):
        self.commands.append(cmd)
        if "--dump-json" in cmd:
            return FakeRun(json.dumps({"duration": self.metadata_duration}))
        if "after_move:filepath" in cmd:
            return FakeRun("/tmp/downloaded.mp4\n")
        if any("localize_video.py" in part for part in cmd):
            raise subprocess.TimeoutExpired(cmd, timeout=600)
        return FakeRun("")


class RecordingNotifier:
    def __init__(self):
        self.progress = []
        self.done = []
        self.documents = []
        self.failed = []
        self.payment_offers = []
        self.limit_notices = []

    def job_progress(self, telegram_id: int, message: str) -> None:
        self.progress.append((telegram_id, message))

    def job_done(self, telegram_id: int, output_path: Path, caption: str | None = None) -> None:
        self.done.append((telegram_id, output_path, caption))

    def document_done(self, telegram_id: int, output_path: Path, caption: str | None = None) -> None:
        self.documents.append((telegram_id, output_path, caption))

    def job_failed(self, telegram_id: int, message: str) -> None:
        self.failed.append((telegram_id, message))

    def job_failed_with_payment_options(self, telegram_id: int, message: str, *, manual_payment_text: str) -> None:
        self.payment_offers.append((telegram_id, message, manual_payment_text))

    def usage_notice(self, telegram_id: int, message: str, *, show_tariffs: bool) -> None:
        self.limit_notices.append((telegram_id, message, show_tariffs))


class TelegramBotWorkerTest(unittest.TestCase):
    def settings(self) -> BotSettings:
        return BotSettings(
            telegram_token="test-token",
            db_path=Path("/tmp/test-bot.db"),
            input_dir=Path("/tmp/input"),
            output_dir=Path("/tmp/output"),
            temp_dir=Path("/tmp/temp"),
            admin_ids=(),
            manual_payment_text="Переведите 50 рублей на номер +79626957711 Тинькофф (только этот банк).",
        )

    def test_processes_next_valid_job_to_done(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=42)
            notifier = RecordingNotifier()

            processed = process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            self.assertEqual(processed["id"], job_id)
            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertIn("/tmp/output/job_", job["message"])
            self.assertEqual(notifier.done, [(1001, Path(job["message"]), None)])
            self.assertEqual(notifier.limit_notices, [(1001, "Осталось бесплатных видео: 2 из 3. Нужно больше? Откройте тарифы.", True)])
            self.assertEqual(notifier.failed, [])
            progress_text = "\n".join(message for _, message in notifier.progress)
            self.assertIn("проверяю", progress_text)
            self.assertIn("примерно", progress_text)
            self.assertIn("скачиваю", progress_text)
            self.assertIn("перевожу", progress_text)
            self.assertEqual(len(runner.commands), 3)
            self.assertIn("--dump-json", runner.commands[0])
            self.assertIn("--merge-output-format", runner.commands[1])
            self.assertIn("localize_video.py", runner.commands[2][1])
        finally:
            db_path.unlink(missing_ok=True)

    def test_processes_legacy_markdown_url_job_with_clean_url(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            dirty_url = (
                "[https://youtube.com/shorts/FrCQCrVn80o?si=EPRuBpwgWpbeZ4Qh]"
                "(https://youtube.com/shorts/FrCQCrVn80o?si=EPRuBpwgWpbeZ4Qh)"
            )
            job_id = create_job(conn, 1001, dirty_url, "youtube", Plan.FREE, None)
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=42)

            process_next_job(conn, self.settings(), runner=runner, notifier=RecordingNotifier())

            clean_url = "https://youtube.com/shorts/FrCQCrVn80o?si=EPRuBpwgWpbeZ4Qh"
            self.assertEqual(runner.commands[0][-1], clean_url)
            self.assertEqual(runner.commands[1][-1], clean_url)
        finally:
            db_path.unlink(missing_ok=True)

    def test_download_job_sends_original_video_without_localizing(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None, mode="download")
            runner = RecordingRunner(metadata_duration=90)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertEqual(notifier.done, [(1001, Path("/tmp/downloaded.mp4"), "Готово. Видео скачано.")])
            self.assertEqual(len(runner.commands), 2)
            self.assertNotIn("localize_video.py", " ".join(runner.commands[-1]))
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_download_job_sends_uploaded_file_without_ytdlp(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "/tmp/upload.mp4", "telegram_upload", Plan.FREE, None, mode="upload_download")
            runner = RecordingRunner(metadata_duration=90)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertEqual(job["message"], "/tmp/upload.mp4")
            self.assertEqual(notifier.done, [(1001, Path("/tmp/upload.mp4"), "Готово. Видео сохранено.")])
            self.assertFalse(any("--dump-json" in cmd for cmd in runner.commands))
        finally:
            db_path.unlink(missing_ok=True)

    def test_clip_job_creates_and_sends_short_clips(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "/tmp/source.mp4", "telegram_upload", Plan.FREE, None, mode="clips")
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=120)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertIn("clips:", job["message"])
            clip_commands = [cmd for cmd in runner.commands if cmd and cmd[0] == "ffmpeg" and "-ss" in cmd]
            self.assertEqual(len(clip_commands), 2)
            self.assertEqual(len(notifier.done), 2)
            self.assertIn("Клип 1", notifier.done[0][2])
            self.assertIn("Клип 2", notifier.done[1][2])
        finally:
            db_path.unlink(missing_ok=True)

    def test_link_clips_job_downloads_then_creates_clips(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None, mode="link_clips")
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=120)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertIn("clips:", job["message"])
            self.assertTrue(any("after_move:filepath" in cmd for cmd in runner.commands))
            self.assertEqual(len([cmd for cmd in runner.commands if cmd and cmd[0] == "ffmpeg" and "-ss" in cmd]), 2)
            self.assertNotIn("localize_video.py", " ".join(" ".join(cmd) for cmd in runner.commands))
        finally:
            db_path.unlink(missing_ok=True)

    def test_upload_transcript_job_creates_text_document(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "/tmp/source.mp4", "telegram_upload", Plan.FREE, None, mode="transcript")
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=120)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertEqual(job["message"], "/tmp/output/job_1_transcript.txt")
            self.assertEqual(notifier.documents, [(1001, Path("/tmp/output/job_1_transcript.txt"), "Готово. Транскрипт готов.")])
            self.assertIn("transcribe_video.py", " ".join(runner.commands[-1]))
        finally:
            db_path.unlink(missing_ok=True)

    def test_link_transcript_job_downloads_then_creates_text_document(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None, mode="transcript")
            consume_free_daily_credit(conn, 1001, job_id=job_id)
            runner = RecordingRunner(metadata_duration=120)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertTrue(any("after_move:filepath" in cmd for cmd in runner.commands))
            self.assertIn("transcribe_video.py", " ".join(runner.commands[-1]))
            self.assertEqual(notifier.documents, [(1001, Path("/tmp/output/job_1_transcript.txt"), "Готово. Транскрипт готов.")])
        finally:
            db_path.unlink(missing_ok=True)

    def test_translation_failure_falls_back_to_downloaded_video(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
            runner = FailingLocalizeRunner(metadata_duration=42)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertIn("download fallback", job["message"])
            self.assertEqual(
                notifier.done,
                [(1001, Path("/tmp/downloaded.mp4"), "Не удалось перевести видео, отправляю скачанный оригинал.")],
            )
            progress_text = "\n".join(message for _, message in notifier.progress)
            self.assertIn("Не удалось перевести", progress_text)
            self.assertEqual(notifier.failed, [])
        finally:
            db_path.unlink(missing_ok=True)

    def test_translation_timeout_falls_back_to_downloaded_video(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.PAID, "zahar")
            runner = TimeoutLocalizeRunner(metadata_duration=42)
            notifier = RecordingNotifier()

            processed = process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            self.assertEqual(processed["status"], "done")
            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "done")
            self.assertIn("слишком много времени", job["message"])
            self.assertEqual(
                notifier.done,
                [(1001, Path("/tmp/downloaded.mp4"), "Не удалось перевести видео, отправляю скачанный оригинал.")],
            )
            self.assertEqual(notifier.failed, [])
        finally:
            db_path.unlink(missing_ok=True)

    def test_rejects_job_when_duration_exceeds_free_limit(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
            runner = RecordingRunner(metadata_duration=70)
            notifier = RecordingNotifier()

            process_next_job(conn, self.settings(), runner=runner, notifier=notifier)

            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "failed")
            self.assertIn("60 секунд", job["message"])
            progress_text = "\n".join(message for _, message in notifier.progress)
            self.assertIn("Видео длится", progress_text)
            self.assertEqual(notifier.failed, [])
            self.assertEqual(
                notifier.payment_offers,
                [(1001, job["message"], "Переведите 50 рублей на номер +79626957711 Тинькофф (только этот банк).")],
            )
            self.assertEqual(len(runner.commands), 1)
        finally:
            db_path.unlink(missing_ok=True)

    def test_builds_telegram_compress_command_under_size_limit(self):
        cmd = build_telegram_compress_command(
            Path("output/source.mp4"),
            Path("output/source_telegram.mp4"),
            duration_seconds=77.0,
        )

        self.assertEqual(cmd[:3], ["ffmpeg", "-y", "-i"])
        self.assertIn("output/source.mp4", cmd)
        self.assertIn("output/source_telegram.mp4", cmd)
        self.assertIn("-b:a", cmd)
        self.assertIn("128k", cmd)
        self.assertTrue(any(part.endswith("k") for part in cmd))

    def test_sanitizes_telegram_token_from_errors(self):
        message = sanitize_error_message(
            "413 Client Error for url: https://api.telegram.org/bot123456:secret/sendVideo"
        )

        self.assertNotIn("123456:secret", message)
        self.assertIn("bot<hidden>", message)

    def test_sanitizes_youtube_antibot_called_process_error(self):
        error = subprocess.CalledProcessError(
            1,
            ["python", "-m", "yt_dlp", "--dump-json", "https://youtube.com/shorts/abc"],
            stderr="ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies",
        )

        message = sanitize_error_message(error)

        self.assertIn("YouTube просит подтвердить", message)
        self.assertIn("cookies", message)
