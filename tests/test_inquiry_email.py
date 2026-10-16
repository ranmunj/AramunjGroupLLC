"""Email routing checks with SMTP and database operations mocked."""

import io
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import server


class InquiryEmailTests(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USERNAME": "test-sender",
            "SMTP_PASSWORD": "test-only-not-a-real-password",
            "SMTP_FROM": "sender@example.com",
        }
        self.payload = {
            "name": "Website Test", "email": "visitor@example.com",
            "company": "Example", "country": "Zimbabwe",
            "project_type": "Software Upgrades & Modernization",
            "message": "Please assess our business application.",
        }
        self.lead = server.validate_lead(self.payload)

    def test_default_recipient_and_reply_to(self):
        with patch.dict(os.environ, self.environment, clear=True), patch.object(server, "deliver_email") as deliver:
            self.assertEqual(server.send_inquiry_email(self.lead), "sent")
        message = deliver.call_args.args[0]
        self.assertEqual(str(message["To"]), "aramunj@icloud.com")
        self.assertEqual(str(message["From"]), "sender@example.com")
        self.assertEqual(str(message["Reply-To"]), "visitor@example.com")
        self.assertIsNone(message["Cc"])
        self.assertIsNone(message["Bcc"])
        self.assertIn("Country: Zimbabwe", message.get_content())
        self.assertIn("Date Submitted:", message.get_content())

    def test_blank_recipient_uses_default(self):
        with patch.dict(os.environ, {**self.environment, "INQUIRY_RECIPIENT": "  "}, clear=True), patch.object(server, "deliver_email") as deliver:
            server.send_inquiry_email(self.lead)
        self.assertEqual(str(deliver.call_args.args[0]["To"]), "aramunj@icloud.com")

    def test_explicit_environment_recipient_is_respected(self):
        with patch.dict(os.environ, {**self.environment, "INQUIRY_RECIPIENT": "aramunj@icloud.com"}, clear=True), patch.object(server, "deliver_email") as deliver:
            server.send_inquiry_email(self.lead)
        self.assertEqual(str(deliver.call_args.args[0]["To"]), "aramunj@icloud.com")

    def test_missing_smtp_does_not_claim_delivery(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(server, "deliver_email") as deliver:
            self.assertEqual(server.send_inquiry_email(self.lead), "not_configured")
            deliver.assert_not_called()

    def test_postgres_save_precedes_email_and_survives_email_failure(self):
        events = []
        raw = json.dumps(self.payload).encode()
        request = SimpleNamespace(
            path="/api/leads", headers={"Content-Length": str(len(raw))},
            rfile=io.BytesIO(raw), get_client_ip=lambda: "192.0.2.1",
        )

        def save(lead):
            events.append("postgres")
            return True

        def email(lead):
            events.append("email")
            raise RuntimeError("Simulated SMTP failure")

        with patch.object(server, "save_to_postgres", side_effect=save), patch.object(server, "send_inquiry_email", side_effect=email), patch.object(server, "save_locally") as local, patch.object(server, "json_response") as response, patch("builtins.print"):
            server.AramunjHandler.do_POST(request)
        self.assertEqual(events, ["postgres", "email"])
        local.assert_not_called()
        self.assertEqual(response.call_args.args[1], 201)
        self.assertEqual(response.call_args.args[2], {"ok": True, "storage": "postgres", "email": "failed"})


if __name__ == "__main__":
    unittest.main()
