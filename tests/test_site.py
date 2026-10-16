"""Static website contract checks; no database or email writes."""

from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.structured_data = ""
        self.in_json = False
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        self.tags.append((tag, attributes))
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json = False

    def handle_data(self, value):
        if self.in_json:
            self.structured_data += value


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = Page((ROOT / "index.html").read_text(encoding="utf-8"))

    def test_unique_ids_and_valid_anchors(self):
        ids = [a["id"] for _, a in self.page.tags if "id" in a]
        self.assertEqual(len(ids), len(set(ids)))
        for tag, attrs in self.page.tags:
            href = attrs.get("href", "")
            if tag == "a" and href.startswith("#"):
                self.assertIn(href[1:], ids)

    def test_assets_exist_and_images_have_alt_dimensions(self):
        for tag, attrs in self.page.tags:
            src = attrs.get("src", "")
            if src and not src.startswith("https:"):
                self.assertTrue((ROOT / src.split("?")[0]).is_file(), src)
            if tag == "img":
                for attribute in ("alt", "width", "height"):
                    self.assertIn(attribute, attrs)

    def test_semantics_and_structured_data(self):
        self.assertEqual(sum(tag == "h1" for tag, _ in self.page.tags), 1)
        data = json.loads(self.page.structured_data)
        self.assertEqual(data["name"], "Aramunj Group LLC")
        self.assertEqual(data["areaServed"], "Worldwide")
        self.assertEqual(data["url"], "https://aramunj.com/")

    def test_contact_preserves_backend_fields(self):
        fields = {a["name"]: a for tag, a in self.page.tags
                  if tag in ("input", "select", "textarea")}
        self.assertEqual(set(fields), {"name", "company", "email", "phone",
                                      "organization", "country", "project_type", "budget", "message"})
        for field in ("name", "email", "project_type", "message"):
            self.assertIn("required", fields[field])
        self.assertEqual(fields["email"]["type"], "email")

    def test_portfolio_and_profile_links(self):
        links = [attrs.get("href") for tag, attrs in self.page.tags if tag == "a"]
        for url in ("https://zgtn.org/", "https://lumibrightzim.com/",
                    "https://www.linkedin.com/in/ranga-munjanja-940926229"):
            self.assertIn(url, links)

    def test_public_contact_address_matches_inquiry_recipient(self):
        mail_links = [attrs["href"] for tag, attrs in self.page.tags
                      if tag == "a" and attrs.get("href", "").startswith("mailto:")]
        self.assertTrue(mail_links)
        self.assertEqual(set(mail_links), {"mailto:aramunj@icloud.com"})
        self.assertEqual(json.loads(self.page.structured_data)["email"], "aramunj@icloud.com")


if __name__ == "__main__":
    unittest.main()
