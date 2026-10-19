from pathlib import Path
import unittest

from telegram_bot.domain import Plan
from telegram_bot.storage import (
    admin_stats,
    clear_pending_voice_request,
    create_job,
    consume_free_daily_credit,
    consume_video_credit,
    create_manual_payment_request,
    get_manual_payment_request,
    get_video_credit_balance,
    get_free_daily_remaining,
    grant_video_package,
    get_pending_voice_request,
    get_job,
    get_next_queued_job,
    get_user_plan,
    init_db,
    requeue_running_jobs,
    set_pending_voice_request,
    update_job_status,
    update_manual_payment_request_status,
    upsert_user,
)


class TelegramBotStorageTest(unittest.TestCase):
    def test_user_defaults_to_free_and_can_be_upgraded(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            self.assertEqual(get_user_plan(conn, 1001), Plan.FREE)
            upsert_user(conn, 1001, Plan.PAID)
            self.assertEqual(get_user_plan(conn, 1001), Plan.PAID)
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_create_and_update_job(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "queued")
            self.assertEqual(job["plan"], "free")
            update_job_status(conn, job_id, "running", "downloading")
            self.assertEqual(get_job(conn, job_id)["status"], "running")
            self.assertEqual(get_job(conn, job_id)["message"], "downloading")
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_next_queued_job_prioritizes_paid_plan(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            free_id = create_job(conn, 1001, "https://youtu.be/free", "youtube", Plan.FREE, None)
            paid_id = create_job(conn, 1002, "https://youtu.be/paid", "youtube", Plan.PAID, "alena")

            next_job = get_next_queued_job(conn)

            self.assertEqual(next_job["id"], paid_id)
            self.assertNotEqual(next_job["id"], free_id)
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_requeue_running_jobs_recovers_after_worker_restart(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
            update_job_status(conn, job_id, "running", "localizing")

            changed = requeue_running_jobs(conn)

            self.assertEqual(changed, 1)
            job = get_job(conn, job_id)
            self.assertEqual(job["status"], "queued")
            self.assertIn("перезапуска", job["message"])
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_pending_voice_request_can_be_saved_replaced_and_cleared(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)

            set_pending_voice_request(conn, 1001, "https://youtu.be/one", "youtube")
            set_pending_voice_request(conn, 1001, "https://youtu.be/two", "youtube")
            pending = get_pending_voice_request(conn, 1001)

            self.assertEqual(pending["url"], "https://youtu.be/two")
            self.assertEqual(pending["source"], "youtube")
            clear_pending_voice_request(conn, 1001)
            self.assertIsNone(get_pending_voice_request(conn, 1001))
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_grant_video_package_adds_paid_and_free_credits(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)

            grant_video_package(conn, 1001, granted_by=10, paid=True)
            grant_video_package(conn, 1001, granted_by=10, paid=True)
            grant_video_package(conn, 1002, granted_by=10, paid=False)

            stats = admin_stats(conn)

            self.assertEqual(get_user_plan(conn, 1001), Plan.PAID)
            self.assertEqual(get_video_credit_balance(conn, 1001), 60)
            self.assertEqual(get_video_credit_balance(conn, 1002), 30)
            self.assertEqual(stats["users_with_credits"], 2)
            self.assertEqual(stats["paid_packages_this_month"], 2)
            self.assertEqual(stats["free_packages_this_month"], 1)
            self.assertEqual(stats["revenue_this_month_rub"], 200)
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_existing_paid_users_are_migrated_to_free_legacy_credit_package(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            upsert_user(conn, 1001, Plan.PAID)
            conn.close()

            conn = init_db(Path("/tmp") / db_path)

            self.assertEqual(get_video_credit_balance(conn, 1001), 30)
            stats = admin_stats(conn)
            self.assertEqual(stats["credits_issued"], 30)
            self.assertEqual(stats["free_packages_this_month"], 0)
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_consumes_video_credit_when_paid_job_is_created(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)
            grant_video_package(conn, 1001, granted_by=10, paid=True)

            self.assertTrue(consume_video_credit(conn, 1001))
            self.assertEqual(get_video_credit_balance(conn, 1001), 29)
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_free_trial_credit_allows_three_videos_total(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)

            self.assertEqual(get_free_daily_remaining(conn, 1001), 3)
            self.assertTrue(consume_free_daily_credit(conn, 1001, job_id=1))
            self.assertEqual(get_free_daily_remaining(conn, 1001), 2)
            self.assertTrue(consume_free_daily_credit(conn, 1001, job_id=2))
            self.assertEqual(get_free_daily_remaining(conn, 1001), 1)
            self.assertTrue(consume_free_daily_credit(conn, 1001, job_id=3))
            self.assertEqual(get_free_daily_remaining(conn, 1001), 0)
            self.assertFalse(consume_free_daily_credit(conn, 1001, job_id=4))
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)

    def test_manual_payment_request_can_be_created_once_and_closed(self):
        db_path = Path(self.id().replace(".", "_")).with_suffix(".db")
        try:
            conn = init_db(Path("/tmp") / db_path)

            first_id = create_manual_payment_request(conn, 1001, username="buyer")
            second_id = create_manual_payment_request(conn, 1001, username="buyer")
            request = get_manual_payment_request(conn, first_id)

            self.assertEqual(first_id, second_id)
            self.assertEqual(request["telegram_id"], 1001)
            self.assertEqual(request["username"], "buyer")
            self.assertEqual(request["status"], "pending")

            self.assertTrue(update_manual_payment_request_status(conn, first_id, "approved", reviewed_by=10))
            self.assertEqual(get_manual_payment_request(conn, first_id)["status"], "approved")
            self.assertFalse(update_manual_payment_request_status(conn, first_id, "rejected", reviewed_by=10))
        finally:
            (Path("/tmp") / db_path).unlink(missing_ok=True)
