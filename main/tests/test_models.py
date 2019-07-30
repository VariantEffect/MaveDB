import datetime

from django.test import TestCase

from ..models import News, SiteInformation
from ..factories import SiteInformationFactory, NewsFactory


class TestNewsModel(TestCase):
    """
    Test that News items can be created, deleted and modified.
    """

    def test_message_property_displays_date_and_text(self):
        message = "Hello World!"
        date = datetime.date.today().replace(1985, 7, 10)
        item = NewsFactory(text=message, creation_date=date)
        self.assertIn(str(item.creation_date), item.message)

    def test_can_retrieve_all_news_items_in_date_order(self):
        item_1 = NewsFactory()
        item_2 = NewsFactory()
        item_3 = NewsFactory()

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
        info = SiteInformationFactory()
        self.assertEqual(SiteInformation.objects.count(), 1)
        self.assertEqual(SiteInformation.objects.all()[0], info)

    def test_can_only_have_one_item(self):
        info_1 = SiteInformationFactory()
        info_2 = SiteInformationFactory()
        self.assertFalse(info_2.can_save())
