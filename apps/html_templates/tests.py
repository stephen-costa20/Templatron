import io
import os
import shutil
import tempfile
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.timezone import now

from .models import Component, ComponentFile


class TempMediaMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmp_media = tempfile.mkdtemp(prefix="test_media_")

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls._tmp_media)
        finally:
            super().tearDownClass()


@override_settings(MEDIA_ROOT=None)  # placeholder so class-level override can apply cleanly
class ComponentsAPITest(TempMediaMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Activate per-class MEDIA_ROOT
        cls.override = override_settings(MEDIA_ROOT=cls._tmp_media)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.override.disable()
        finally:
            super().tearDownClass()

    def setUp(self):
        self.list_url = reverse('apps.html_templates:html_templates_create')
        self.home_url = reverse('apps.html_templates:home')

    # 1) Home page render
    def test_home_page_renders(self):
        res = self.client.get(self.home_url)
        self.assertEqual(res.status_code, 200)
        # Template name depends on your configure; asserting content is safer
        self.assertIn(b'Add New Code', res.content)

    # 2) JSON create -> list -> detail
    def test_create_component_json_and_list_and_detail(self):
        payload = {
            "name": "Card A",
            "section": "UI Components",
            "tags": ["widget", "table"],
            "code": "<div>Hello A</div>",
            "description": "Short desc",
            "notes": "Internal note",
            "instructions": "1) Do X\n2) Do Y",
        }
        create_res = self.client.post(self.list_url, data=payload, content_type='application/json')
        self.assertEqual(create_res.status_code, 201, create_res.content)
        created = create_res.json()
        self.assertIn('id', created)
        self.assertEqual(created['name'], 'Card A')
        self.assertEqual(created['section'], 'UI Components')
        self.assertEqual(created['tags'], ["widget", "table"])
        self.assertEqual(created['code'], "<div>Hello A</div>")
        self.assertTrue(created['dateISO'])

        # list
        list_res = self.client.get(self.list_url)
        self.assertEqual(list_res.status_code, 200)
        results = list_res.json().get('results', [])
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Card A')

        # detail
        detail_url = reverse('apps.html_templates:html_templates_detail', kwargs={'pk': created['id']})
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, 200)
        detail = detail_res.json()
        self.assertEqual(detail['name'], 'Card A')
        self.assertEqual(detail['files'], [])

        # model helpers
        obj = Component.objects.get(pk=created['id'])
        self.assertEqual(obj.tag_list(), ["widget", "table"])
        self.assertEqual(obj.to_dict()['tags'], ["widget", "table"])

    # 3) Multipart create (upload mode) with code file + attachments
    def test_create_component_multipart_with_code_file_and_attachments(self):
        code_file = SimpleUploadedFile("snippet.html", b"<section>Upload Code</section>", content_type="text/html")
        attach1 = SimpleUploadedFile("doc.txt", b"alpha", content_type="text/plain")
        attach2 = SimpleUploadedFile("image.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")

        data = {
            "name": "Card Upload",
            "section": "Blocks",
            "tags": "alpha, beta",
            "description": "From file",
            "notes": "N/A",
            "instructions": "Install then import",
        }
        # Files dict: keep keys separate from 'data'
        files = {
            "code_file": code_file,
            "files": [attach1, attach2],
        }

        res = self.client.post(self.list_url, data={**data, **files})
        self.assertEqual(res.status_code, 201, res.content)
        out = res.json()
        self.assertEqual(out['name'], 'Card Upload')
        self.assertIn('Upload Code', out['code'])  # came from uploaded file

        # detail should include 2 files
        detail_url = reverse('apps.html_templates:html_templates_detail', kwargs={'pk': out['id']})
        dres = self.client.get(detail_url)
        self.assertEqual(dres.status_code, 200)
        detail = dres.json()
        self.assertIn('files', detail)
        self.assertEqual(len(detail['files']), 2)

        # DB objects created
        self.assertTrue(ComponentFile.objects.filter(component_id=out['id']).count(), 2)

    # 4) Validation: missing code (JSON and multipart)
    def test_create_component_json_requires_code(self):
        payload = {"name": "No Code", "section": "X", "tags": [], "code": ""}
        res = self.client.post(self.list_url, data=payload, content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_create_component_multipart_requires_code(self):
        # Neither code_text nor code_file provided
        res = self.client.post(self.list_url, data={"name": "No Code Upload", "section": "Y"})
        self.assertEqual(res.status_code, 400)

    # 5) PATCH updates: fields, tags (list->csv), dateISO override
    def test_patch_updates_fields_tags_and_date(self):
        # seed
        create = self.client.post(
            self.list_url,
            data={"name": "Seed", "section": "S", "tags": ["a"], "code": "<div>Seed</div>"},
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 201)
        cid = create.json()['id']
        detail_url = reverse('apps.html_templates:html_templates_detail', kwargs={'pk': cid})

        patch_payload = {
            "name": "Seed v2",
            "section": "S2",
            "tags": ["a", "b", "c"],
            "notes": "Updated note",
            "dateISO": "2024-01-15",
        }
        pres = self.client.patch(detail_url, data=patch_payload, content_type='application/json')
        self.assertEqual(pres.status_code, 200, pres.content)
        updated = pres.json()
        self.assertEqual(updated['name'], "Seed v2")
        self.assertEqual(updated['section'], "S2")
        self.assertEqual(updated['tags'], ["a", "b", "c"])
        self.assertEqual(updated['dateISO'], "2024-01-15")

        # confirm db row
        obj = Component.objects.get(pk=cid)
        self.assertEqual(obj.name, "Seed v2")
        self.assertEqual(obj.section, "S2")
        self.assertEqual(obj.tag_list(), ["a", "b", "c"])
        self.assertEqual(obj.date_added.isoformat(), "2024-01-15")

    # 6) DELETE removes record
    def test_delete_component(self):
        r = self.client.post(
            self.list_url,
            data={"name": "To Delete", "section": "", "tags": [], "code": "<div>x</div>"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        cid = r.json()['id']
        detail_url = reverse('apps.html_templates:html_templates_detail', kwargs={'pk': cid})

        dres = self.client.delete(detail_url)
        self.assertEqual(dres.status_code, 200)
        self.assertFalse(Component.objects.filter(pk=cid).exists())

    # 7) Ordering check on list endpoint
    def test_list_ordering_by_date_then_name(self):
        # Create two records with same date via dateISO patch to control ordering
        r1 = self.client.post(
            self.list_url,
            data={"name": "Alpha", "section": "", "tags": [], "code": "<div>a</div>"},
            content_type="application/json",
        )
        r2 = self.client.post(
            self.list_url,
            data={"name": "Bravo", "section": "", "tags": [], "code": "<div>b</div>"},
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)

        # set same date for both; list ordering then falls back to name ascending
        for cid in (r1.json()['id'], r2.json()['id']):
            detail_url = reverse('apps.html_templates:html_templates_detail', kwargs={'pk': cid})
            self.client.patch(detail_url, data={"dateISO": "2024-06-01"}, content_type="application/json")

        # fetch list (ordered by -date_added, name)
        # same date -> name ascending => Alpha before Bravo
        lst = self.client.get(self.list_url).json()['results']
        names = [x['name'] for x in lst if x['dateISO'] == "2024-06-01"][:2]
        self.assertEqual(names, ["Alpha", "Bravo"])