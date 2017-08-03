
import datetime

from django.test import TransactionTestCase
from django.core.exceptions import ValidationError

from ..models import News
from ..models import SiteInformation


class TestNewsModel(TransactionTestCase):
    """
    Test that News items can be created, deleted and modified.
    """
    reset_sequences = True

    def test_create_and_save_new_item(self):
        item = News(text="Hello World!")
        item.save()
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.all()[0], item)

    def test_message_property_displays_date_and_text(self):
        message = "Hello World!"
        date = datetime.date.today().replace(1985, 7, 10)
        expected = "[{}]: {}".format(str(date), message)

        item = News(text=message, date=date)
        self.assertEqual(expected, item.message)

    def test_DONT_allow_null_message(self):
        item = News(text=None, date=datetime.date.today())
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_DONT_allow_null_date(self):
        item = News(text="Hello World", date=None)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_DONT_allow_non_YYYY_MM_DD_date_format(self):
        item = News(text="Hello World", date=datetime.datetime.now())
        with self.assertRaises(ValueError):
            item.save()

    def test_DONT_allow_a_blank_message(self):
        item = News(text="")
        with self.assertRaises(ValueError):
            item.save()

    def test_can_retrieve_all_news_items_in_date_order(self):
        item_1 = News.objects.create(text="Hello World!")
        item_2 = News.objects.create(text="Nice Weather!")
        item_3 = News.objects.create(text="Nothing new to report!")

        item_2.date += datetime.timedelta(days=1)
        item_3.date += datetime.timedelta(days=2)

        item_2.save()
        item_3.save()

        news_items = News.recent_news()
        self.assertEqual(len(News.recent_news()), 3)
        self.assertEqual(news_items[0], item_3)
        self.assertEqual(news_items[1], item_2)
        self.assertEqual(news_items[2], item_1)


class SiteInformationModelTest(TransactionTestCase):
    """
    Test that a SiteInformation can be created, deleted and modified.
    """

    reset_sequences = True

    def test_can_create_and_save_information(self):
        info = SiteInformation.objects.create(
            about="This is MaveDB", citation="This is a citation.")
        self.assertEqual(SiteInformation.objects.count(), 1)
        self.assertEqual(SiteInformation.objects.all()[0], info)

    def test_can_only_have_one_item(self):
        info_1 = SiteInformation.objects.create(
            about="This is MaveDB",
            citation="This is a citation.")
        with self.assertRaises(ValueError):
            info_2 = SiteInformation.objects.create(
                about="This is another MaveDB",
                citation="This is a another citation.")

    def test_can_edit_and_save_existing_item(self):
        info_1 = SiteInformation.objects.create(
            about="This is MaveDB",
            citation="This is a citation.")

        info_1.about = "New about information."
        info_1.citation = "New citation."
        info_1.save()
        self.assertEqual(info_1.about, "New about information.")
        self.assertEqual(info_1.citation, "New citation.")

    def test_DONT_allow_empty_about_text(self):
        with self.assertRaises(ValueError):
            SiteInformation.objects.create(
                about="",
                citation="This is a citation."
            )

    def test_DONT_allow_null_about_text(self):
        with self.assertRaises(ValueError):
            SiteInformation.objects.create(
                about=None,
                citation="This is a citation."
            )

    def test_DONT_allow_empty_citation_text(self):
        with self.assertRaises(ValueError):
            SiteInformation.objects.create(
                about="This is MaveDB",
                citation=""
            )

    def test_DONT_allow_null_citation_text(self):
        with self.assertRaises(ValueError):
            SiteInformation.objects.create(
                about="This is MaveDB",
                citation=None
            )
