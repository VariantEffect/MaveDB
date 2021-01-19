from django.test import Client, TestCase
from django.urls import reverse

from .. import views
from .. import models
from accounts.models import User
from dataset import constants
from dataset.factories import ScoreSetFactory
from dataset.models.scoreset import ScoreSet
from main.models import News
from urn.models import generate_tmp_urn, get_model_by_urn


class TestManagerView(TestCase):
    def setUp(self):
        self.client = Client()
        self.manage_url = reverse('manager:manage')
        self.subcommand_keys = ['addpmid', 'adduser', 'createnews']
        self.user = User(username='user')
        self.user.set_password('password')
        self.user.save()
        self.poweruser = User(username='poweruser')
        self.poweruser.set_password('password')
        self.poweruser.save()
        self.poweruser.userrole.role = models.Role.POWERUSER
        self.poweruser.save()

    def test_correct_authorization(self):
        # First, test that it redirects to login page (302)
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 302)

        # Then, that it raises a permissions error (403)
        self.client.login(username='user', password='password')
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 403)

        # And finally, that it succeeds
        self.client.logout()
        self.client.login(username='poweruser', password='password')
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 200)

    def test_has_subcommands(self):
        self.client.login(username='poweruser', password='password')
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 200)
        for key in response.context['subcommands'].keys():
            self.assertTrue(key in self.subcommand_keys)
        for key in self.subcommand_keys:
            self.assertTrue(key in response.context['subcommands'].keys())


class TestAddPmidView(TestCase):
    def setUp(self):
        self.client = Client()
        self.poweruser = User(username='poweruser')
        self.poweruser.set_password('password')
        self.poweruser.save()
        self.poweruser.userrole.role = models.Role.POWERUSER
        self.poweruser.save()
        self.client.login(username='poweruser', password='password')
        self.addpmid_url = reverse('manager:manage_addpmid')
        self.pmid = '29103961'
        _ = ScoreSetFactory()

    def test_addpmid_view_loads(self):
        response = self.client.get(self.addpmid_url)
        self.assertEqual(response.status_code, 200)

    def test_add_pmid_to_urn(self):
        response = self.client.get(self.addpmid_url)
        urns = response.context['urns']
        urn = urns[0]
        instance = get_model_by_urn(urn)
        instance_pmids = [pmid.identifier for pmid in instance.pubmed_ids.all()]
        self.assertFalse(self.pmid in instance_pmids)

        data = {
            'urn': urn,
            'pmid': self.pmid
        }
        response = self.client.post(self.addpmid_url, data)
        self.assertEqual(response.status_code, 200)
        instance = get_model_by_urn(urn)
        instance_pmids = [pmid.identifier for pmid in instance.pubmed_ids.all()]
        self.assertTrue(self.pmid in instance_pmids)


class TestAddUserView(TestCase):
    def setUp(self):
        self.client = Client()
        self.poweruser = User(username='poweruser')
        self.poweruser.set_password('password')
        self.poweruser.save()
        self.poweruser.userrole.role = models.Role.POWERUSER
        self.poweruser.save()
        self.client.login(username='poweruser', password='password')
        self.adduser_url = reverse('manager:manage_adduser')
        self.orcid_id = '0000-0002-2781-7390'
        u = User.objects.create(username=self.orcid_id)
        u.save()
        self.user = User.objects.get(username=self.orcid_id)
        _ = ScoreSetFactory()

    def test_adduser_view_loads(self):
        response = self.client.get(self.adduser_url)
        self.assertEqual(response.status_code, 200)

    def test_add_administrator_to_urn(self):
        response = self.client.get(self.adduser_url)
        urns = response.context['urns']
        urn = urns[0]
        role = constants.administrator

        instance = get_model_by_urn(urn)
        administrators = instance.administrators
        self.assertFalse(self.user in administrators)

        data = {
            'urn': urn,
            'orcid_id': self.orcid_id,
            'role': role
        }
        response = self.client.post(self.adduser_url, data)
        self.assertEqual(response.status_code, 200)
        instance = get_model_by_urn(urn)
        administrators = instance.administrators
        self.assertTrue(self.user in administrators)


    def test_add_editor_to_urn(self):
        response = self.client.get(self.adduser_url)
        urns = response.context['urns']
        urn = urns[0]
        role = constants.editor

        instance = get_model_by_urn(urn)
        editors = instance.editors
        self.assertFalse(self.user in editors)

        data = {
            'urn': urn,
            'orcid_id': self.orcid_id,
            'role': role
        }
        response = self.client.post(self.adduser_url, data)
        self.assertEqual(response.status_code, 200)
        instance = get_model_by_urn(urn)
        editors = instance.editors
        self.assertTrue(self.user in editors)

    def test_add_viewer_to_urn(self):
        response = self.client.get(self.adduser_url)
        urns = response.context['urns']
        urn = urns[0]
        role = constants.viewer

        instance = get_model_by_urn(urn)
        viewers = instance.viewers
        self.assertFalse(self.user in viewers)

        data = {
            'urn': urn,
            'orcid_id': self.orcid_id,
            'role': role
        }
        response = self.client.post(self.adduser_url, data)
        self.assertEqual(response.status_code, 200)
        instance = get_model_by_urn(urn)
        viewers = instance.viewers
        self.assertTrue(self.user in viewers)


class TestCreateNewsView(TestCase):
    def setUp(self):
        self.client = Client()
        self.poweruser = User(username='poweruser')
        self.poweruser.set_password('password')
        self.poweruser.save()
        self.poweruser.userrole.role = models.Role.POWERUSER
        self.poweruser.save()
        self.client.login(username='poweruser', password='password')
        self.createnews_url = reverse('manager:manage_createnews')
        self.levels = [status_choice[0] for status_choice in News.STATUS_CHOICES]

    def test_createnews_view_loads(self):
        response = self.client.get(self.createnews_url)
        self.assertEqual(response.status_code, 200)

    def test_can_publish_news_all_levels(self):
        num_published = 0
        self.assertEqual(len(News.objects.all()), num_published)

        for level in self.levels:
            data = {
                'message': 'This is cool news!',
                'level': level
            }
            response = self.client.post(self.createnews_url, data)
            self.assertEqual(response.status_code, 200)
            num_published = num_published + 1
            self.assertEqual(len(News.objects.all()), num_published)
