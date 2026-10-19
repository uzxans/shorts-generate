import unittest
from pathlib import Path

from telegram_bot.bot_app import (
    BUY_SUBSCRIPTION_MESSAGE,
    admin_stats_message,
    approve_manual_payment_request,
    build_manual_payment_admin_message,
    build_manual_payment_user_message,
    build_paid_voice_keyboard_rows,
    choose_paid_voice_for_pending_link,
    choose_processing_action_for_pending_link,
    create_clip_job_from_uploaded_video,
    create_job_from_user_link,
    create_uploaded_video_action_request,
    format_job_status,
    grant_paid,
    grant_subscription_command,
    handle_alt_payment_request,
    handle_manual_payment_confirmation,
    is_video_upload_message,
    parse_grant_paid_target,
    parse_link_message,
    parse_status_job_id,
    reject_manual_payment_request,
    subscription_offer_message,
)
from telegram_bot.domain import Plan
from telegram_bot.storage import (
    admin_stats,
    get_manual_payment_request,
    grant_video_package,
    get_job,
    get_pending_voice_request,
    get_pending_action_request,
    get_user_plan,
    get_video_credit_balance,
    get_free_daily_remaining,
    consume_free_daily_credit,
    init_db,
    update_job_status,
    upsert_user,
)


class TelegramBotAppTest(unittest.TestCase):
    def test_detects_uploaded_video_documents_by_mime_type_or_filename(self):
        class Document:
            def __init__(self, mime_type=None, file_name=None):
                self.mime_type = mime_type
                self.file_name = file_name

        class Message:
            def __init__(self, *, video=None, video_note=None, document=None):
                self.video = video
                self.video_note = video_note
                self.document = document

        self.assertTrue(is_video_upload_message(Message(video=object())))
        self.assertTrue(is_video_upload_message(Message(video_note=object())))
        self.assertTrue(is_video_upload_message(Message(document=Document(mime_type="video/mp4"))))
        self.assertTrue(is_video_upload_message(Message(document=Document(mime_type="application/octet-stream", file_name="clip.MP4"))))
        self.assertFalse(is_video_upload_message(Message(document=Document(mime_type="application/pdf", file_name="file.pdf"))))

    def test_rejects_unsupported_link_before_creating_job(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            result = create_job_from_user_link(conn, 1001, "https://example.com/video")

            self.assertFalse(result.ok)
            self.assertIsNone(result.job_id)
            self.assertIn("YouTube или Instagram", result.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_creates_job_with_user_plan_and_source(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            grant_video_package(conn, 1001, granted_by=10, paid=True)

            create_job_from_user_link(conn, 1001, "https://youtu.be/abc", requested_voice="alena")
            result = choose_processing_action_for_pending_link(conn, 1001, "translate")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            self.assertIn("примерно", result.message)
            self.assertIn("/status", result.message)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["plan"], "paid")
            self.assertEqual(job["source"], "youtube")
            self.assertEqual(job["voice"], "alena")
            self.assertEqual(job["mode"], "translate")
        finally:
            db_path.unlink(missing_ok=True)

    def test_link_waits_for_product_action_choice(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = create_job_from_user_link(conn, 1001, "https://www.instagram.com/reel/abc/")

            self.assertTrue(result.ok)
            self.assertIsNone(result.job_id)
            self.assertTrue(result.needs_action_choice)
            self.assertIn("Что подготовить", result.message)
            pending = get_pending_action_request(conn, 1001)
            self.assertEqual(pending["url"], "https://www.instagram.com/reel/abc/")
            self.assertEqual(pending["source"], "instagram")
        finally:
            db_path.unlink(missing_ok=True)

    def test_download_choice_creates_download_job_without_translation(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            remaining_before = get_free_daily_remaining(conn, 1001)
            create_job_from_user_link(conn, 1001, "https://youtu.be/abc")

            result = choose_processing_action_for_pending_link(conn, 1001, "download")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "download")
            self.assertEqual(job["plan"], "free")
            self.assertIsNone(get_pending_action_request(conn, 1001))
            self.assertEqual(get_free_daily_remaining(conn, 1001), remaining_before)
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_video_creates_clip_job_for_free_user(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = create_clip_job_from_uploaded_video(conn, 1001, Path("/tmp/upload.mp4"))

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "clips")
            self.assertEqual(job["source"], "telegram_upload")
            self.assertEqual(job["url"], "/tmp/upload.mp4")
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_video_waits_for_user_action_before_creating_job(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = create_uploaded_video_action_request(conn, 1001, Path("/tmp/upload.mp4"))

            self.assertTrue(result.ok)
            self.assertTrue(result.needs_action_choice)
            self.assertIsNone(result.job_id)
            pending = get_pending_action_request(conn, 1001)
            self.assertEqual(pending["source"], "telegram_upload")
            self.assertEqual(pending["url"], "/tmp/upload.mp4")
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_video_action_creates_clip_job(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            create_uploaded_video_action_request(conn, 1001, Path("/tmp/upload.mp4"))

            result = choose_processing_action_for_pending_link(conn, 1001, "clips")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "clips")
            self.assertEqual(job["source"], "telegram_upload")
            self.assertIsNone(get_pending_action_request(conn, 1001))
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_video_download_action_is_not_offered_as_useful_action(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            remaining_before = get_free_daily_remaining(conn, 1001)
            create_uploaded_video_action_request(conn, 1001, Path("/tmp/upload.mp4"))

            result = choose_processing_action_for_pending_link(conn, 1001, "download")

            self.assertFalse(result.ok)
            self.assertIn("Видео уже у вас", result.message)
            self.assertEqual(get_free_daily_remaining(conn, 1001), remaining_before)
        finally:
            db_path.unlink(missing_ok=True)

    def test_link_clips_action_creates_clip_job_and_consumes_trial(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            create_job_from_user_link(conn, 1001, "https://www.instagram.com/reel/abc/")

            result = choose_processing_action_for_pending_link(conn, 1001, "clips")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "link_clips")
            self.assertEqual(job["source"], "instagram")
            self.assertEqual(get_free_daily_remaining(conn, 1001), 2)
        finally:
            db_path.unlink(missing_ok=True)

    def test_link_transcript_action_creates_transcript_job_and_consumes_trial(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            create_job_from_user_link(conn, 1001, "https://www.instagram.com/reel/abc/")

            result = choose_processing_action_for_pending_link(conn, 1001, "transcript")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "transcript")
            self.assertEqual(job["source"], "instagram")
            self.assertEqual(get_free_daily_remaining(conn, 1001), 2)
        finally:
            db_path.unlink(missing_ok=True)

    def test_uploaded_video_transcript_action_creates_transcript_job(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            create_uploaded_video_action_request(conn, 1001, Path("/tmp/upload.mp4"))

            result = choose_processing_action_for_pending_link(conn, 1001, "transcript")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["mode"], "transcript")
            self.assertEqual(job["source"], "telegram_upload")
            self.assertEqual(job["url"], "/tmp/upload.mp4")
            self.assertEqual(get_free_daily_remaining(conn, 1001), 2)
        finally:
            db_path.unlink(missing_ok=True)

    def test_free_user_without_trial_limit_can_download_but_cannot_translate(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            consume_free_daily_credit(conn, 1001, job_id=1)
            consume_free_daily_credit(conn, 1001, job_id=2)
            consume_free_daily_credit(conn, 1001, job_id=3)
            create_job_from_user_link(conn, 1001, "https://youtu.be/abc")

            download_result = choose_processing_action_for_pending_link(conn, 1001, "download")
            create_job_from_user_link(conn, 1001, "https://youtu.be/def")
            translate_result = choose_processing_action_for_pending_link(conn, 1001, "translate")

            self.assertTrue(download_result.ok)
            self.assertFalse(translate_result.ok)
            self.assertTrue(translate_result.needs_tariff_button)
            self.assertIn("3 бесплатных видео", translate_result.message)
            self.assertIn("Тарифы", translate_result.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_parses_link_message_with_optional_voice(self):
        parsed = parse_link_message("https://youtu.be/abc voice=alena")

        self.assertEqual(parsed.url, "https://youtu.be/abc")
        self.assertEqual(parsed.voice, "alena")

    def test_parses_markdown_link_as_clean_url(self):
        parsed = parse_link_message(
            "[https://youtube.com/shorts/7CuocteUapM?si=6Xtiflex9TgoOFSo](https://youtube.com/shorts/7CuocteUapM?si=6Xtiflex9TgoOFSo)"
        )

        self.assertEqual(parsed.url, "https://youtube.com/shorts/7CuocteUapM?si=6Xtiflex9TgoOFSo")

    def test_free_user_cannot_request_voice_before_job_is_created(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = create_job_from_user_link(conn, 1001, "https://youtu.be/abc voice=alena")

            self.assertFalse(result.ok)
            self.assertIn("выбор голоса", result.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_paid_user_cannot_request_unknown_voice(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            grant_video_package(conn, 1001, granted_by=10, paid=True)

            result = create_job_from_user_link(conn, 1001, "https://youtu.be/abc voice=unknown")

            self.assertFalse(result.ok)
            self.assertIn("Голос недоступен", result.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_paid_user_link_without_voice_waits_for_button_choice(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            grant_video_package(conn, 1001, granted_by=10, paid=True)

            link_result = create_job_from_user_link(conn, 1001, "https://youtu.be/abc")
            result = choose_processing_action_for_pending_link(conn, 1001, "translate")

            self.assertTrue(link_result.needs_action_choice)
            self.assertTrue(result.ok)
            self.assertIsNone(result.job_id)
            self.assertTrue(result.needs_voice_choice)
            self.assertIn("выберите голос", result.message.lower())
            pending = get_pending_voice_request(conn, 1001)
            self.assertEqual(pending["url"], "https://youtu.be/abc")
        finally:
            db_path.unlink(missing_ok=True)

    def test_paid_voice_keyboard_has_preview_and_select_for_yandex_voices(self):
        rows = build_paid_voice_keyboard_rows()

        self.assertIn(("Послушать Alena", "voice_sample:alena"), rows)
        self.assertIn(("Выбрать Alena", "voice:alena"), rows)
        self.assertIn(("Послушать Zahar", "voice_sample:zahar"), rows)
        self.assertIn(("Выбрать Zahar", "voice:zahar"), rows)

    def test_paid_voice_choice_creates_job_from_pending_link(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            grant_video_package(conn, 1001, granted_by=10, paid=True)
            create_job_from_user_link(conn, 1001, "https://youtu.be/abc")
            choose_processing_action_for_pending_link(conn, 1001, "translate")

            result = choose_paid_voice_for_pending_link(conn, 1001, "zahar")

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.job_id)
            job = get_job(conn, result.job_id)
            self.assertEqual(job["plan"], "paid")
            self.assertEqual(job["voice"], "zahar")
            self.assertEqual(job["url"], "https://youtu.be/abc")
            self.assertIsNone(get_pending_voice_request(conn, 1001))
        finally:
            db_path.unlink(missing_ok=True)

    def test_admin_can_grant_paid_plan(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            denied = grant_paid(conn, actor_id=999, target_id=1001, admin_ids=(10,))
            allowed = grant_paid(conn, actor_id=10, target_id=1001, admin_ids=(10,))

            self.assertFalse(denied.ok)
            self.assertTrue(allowed.ok)
            self.assertEqual(get_user_plan(conn, 1001), Plan.PAID)
        finally:
            db_path.unlink(missing_ok=True)

    def test_admin_can_grant_free_video_package_to_friends(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = grant_subscription_command(conn, actor_id=10, target_id=1001, admin_ids=(10,), paid=False)

            self.assertTrue(result.ok)
            self.assertIn("бесплатно", result.message)
            self.assertEqual(get_user_plan(conn, 1001), Plan.PAID)
        finally:
            db_path.unlink(missing_ok=True)

    def test_admin_stats_message_shows_users_revenue_and_credit_packages(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            upsert_user(conn, 1001, Plan.FREE)
            grant_subscription_command(conn, actor_id=10, target_id=1002, admin_ids=(10,), paid=True)

            denied = admin_stats_message(conn, actor_id=11, admin_ids=(10,))
            allowed = admin_stats_message(conn, actor_id=10, admin_ids=(10,))

            self.assertFalse(denied.ok)
            self.assertIn("Пользователей", allowed.message)
            self.assertIn("Пользователей с видео: 1", allowed.message)
            self.assertIn("Доход за месяц: 100 руб", allowed.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_paid_user_needs_credits_before_voice_choice(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            upsert_user(conn, 1001, Plan.PAID)

            link_result = create_job_from_user_link(conn, 1001, "https://youtu.be/last")
            result = choose_processing_action_for_pending_link(conn, 1001, "translate")

            self.assertTrue(link_result.needs_action_choice)
            self.assertFalse(result.ok)
            self.assertIn("закончились", result.message)
            self.assertIn("ещё пакет", result.message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_subscription_offer_text_sells_paid_plan(self):
        text = subscription_offer_message()

        self.assertIn("100 рублей", text)
        self.assertIn("дешевле кофе", text)
        self.assertIn("30 видео", text)
        self.assertIn("20 минут", text)
        self.assertIn("готовые клипы для публикации", text)
        self.assertIn("+30 видео", BUY_SUBSCRIPTION_MESSAGE)
        self.assertIn("докупите", BUY_SUBSCRIPTION_MESSAGE)

    def test_builds_manual_payment_user_message_with_admin_payment_instruction(self):
        message = build_manual_payment_user_message(
            telegram_id=1001,
            manual_payment_text="чтоб получить реквизиты для оплаты напишите админу @timm_dev",
        )

        self.assertIn("100 рублей", message)
        self.assertIn("30 видео", message)
        self.assertIn("1001", message)
        self.assertIn("@timm_dev", message)
        self.assertNotIn("+79626957711", message)
        self.assertNotIn("Тинькофф", message)
        self.assertNotIn("YooMoney", message)
        self.assertIn("Я оплатил", message)

    def test_manual_payment_confirmation_creates_admin_request(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)

            result = handle_manual_payment_confirmation(conn, telegram_id=1001, username="buyer")
            admin_message = build_manual_payment_admin_message(
                request_id=result.request_id,
                telegram_id=1001,
                username="buyer",
            )

            self.assertTrue(result.ok)
            self.assertIsNotNone(result.request_id)
            self.assertIn("проверю оплату", result.message)
            self.assertIn("@buyer", admin_message)
            self.assertIn("1001", admin_message)
            self.assertIn("Начислить +30", admin_message)
        finally:
            db_path.unlink(missing_ok=True)

    def test_admin_can_approve_or_reject_manual_payment_request(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            approve_request = handle_manual_payment_confirmation(conn, telegram_id=1001, username="buyer")
            reject_request = handle_manual_payment_confirmation(conn, telegram_id=1002, username="other")

            denied = approve_manual_payment_request(conn, request_id=approve_request.request_id, actor_id=99, admin_ids=(10,))
            approved = approve_manual_payment_request(conn, request_id=approve_request.request_id, actor_id=10, admin_ids=(10,))
            duplicate = approve_manual_payment_request(conn, request_id=approve_request.request_id, actor_id=10, admin_ids=(10,))
            rejected = reject_manual_payment_request(conn, request_id=reject_request.request_id, actor_id=10, admin_ids=(10,))

            self.assertFalse(denied.ok)
            self.assertTrue(approved.ok)
            self.assertIn("+30 видео", approved.user_message)
            self.assertFalse(duplicate.ok)
            self.assertTrue(rejected.ok)
            self.assertEqual(get_video_credit_balance(conn, 1001), 30)
            self.assertEqual(get_video_credit_balance(conn, 1002), 0)
            self.assertEqual(get_manual_payment_request(conn, approve_request.request_id)["status"], "approved")
            self.assertEqual(get_manual_payment_request(conn, reject_request.request_id)["status"], "rejected")
            self.assertEqual(admin_stats(conn)["revenue_this_month_rub"], 100)
        finally:
            db_path.unlink(missing_ok=True)

    def test_alt_payment_request_tells_user_admin_will_contact_them(self):
        result = handle_alt_payment_request(telegram_id=1001, username="buyer", alt_payment_text="Напишите страну и удобный способ оплаты.")

        self.assertTrue(result.ok)
        self.assertIn("Напишите страну", result.message)
        self.assertIn("1001", result.admin_message)

    def test_formats_job_status_for_owner(self):
        db_path = Path("/tmp") / Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(db_path)
            create_job_from_user_link(conn, 1001, "https://youtu.be/abc")
            result = choose_processing_action_for_pending_link(conn, 1001, "translate")
            update_job_status(conn, result.job_id, "running", "downloading")

            owner_status = format_job_status(conn, result.job_id, requester_id=1001)
            other_status = format_job_status(conn, result.job_id, requester_id=2002)

            self.assertIn("running", owner_status.message)
            self.assertIn("downloading", owner_status.message)
            self.assertFalse(other_status.ok)
        finally:
            db_path.unlink(missing_ok=True)

    def test_parses_command_arguments(self):
        self.assertEqual(parse_grant_paid_target("/grant_paid 1001"), 1001)
        self.assertIsNone(parse_grant_paid_target("/grant_paid"))
        self.assertEqual(parse_status_job_id("/status 42"), 42)
        self.assertIsNone(parse_status_job_id("/status nope"))
