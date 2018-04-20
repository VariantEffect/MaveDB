import datetime

from django.test import TestCase
from django.core.exceptions import ValidationError

from ..models import News
from ..models import SiteInformation


class TestNewsModel(TestCase):
    """
    Test that News items can be created, deleted and modified.
    """
    def test_create_and_save_new_item(self):
        item = News(text="Hello World!")
        item.save()
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.all()[0], item)

    def test_message_property_displays_date_and_text(self):
        message = "Hello World!"
        date = datetime.date.today().replace(1985, 7, 10)
        expected = "[{}]: {}".format(str(date), message)

        item = News(text=message, creation_date=date)
        self.assertEqual(expected, item.message)

    def test_can_retrieve_all_news_items_in_date_order(self):
        item_1 = News.objects.create(text="Hello World!")
        item_2 = News.objects.create(text="Nice Weather!")
        item_3 = News.objects.create(text="Nothing new to report!")

        item_2.creation_date += datetime.timedelta(days=1)
        item_3.creation_date += datetime.timedelta(days=2)

        item_2.save()
        item_3.save()

        news_items = News.recent_news()
        self.assertEqual(len(News.recent_news()), 3)
        self.assertEqual(news_items[0], item_3)
        self.assertEqual(news_items[1], item_2)
        self.assertEqual(news_items[2], item_1)


class SiteInformationModelTest(TestCase):
    """
    Test that a SiteInformation can be created, deleted and modified.
    """
    def test_can_create_and_save_information(self):
        info = SiteInformation.objects.create(
            about="This is MaveDB", citation="This is a citation.")
        self.assertEqual(SiteInformation.objects.count(), 1)
        self.assertEqual(SiteInformation.objects.all()[0], info)

    def test_can_only_have_one_item(self):
        info_1 = SiteInformation.objects.create(
            about="This is MaveDB",
            citation="This is a citation.")
        info_2 = SiteInformation(
            about="This is another MaveDB",
            citation="This is a another citation.")
        self.assertFalse(info_2.can_save())

    def test_can_edit_and_save_existing_item(self):
        info_1 = SiteInformation.objects.create(
            about="This is MaveDB",
            citation="This is a citation."
        )

        info_1.about = "New about information."
        info_1.citation = "New citation."
        info_1.save()
        self.assertIn("New about information.", info_1.about)
        self.assertIn("New citation.", info_1.citation)