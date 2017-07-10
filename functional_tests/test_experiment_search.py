
"""
Functional testing suite that will test that experiments can be searched
by each database field correctly using the column-wise search boxes
and that advanced search functions as expected.
"""

from .base import FunctionalTest


class SearchFunctionalityTest(FunctionalTest):

    def setUp(self):
        # Setup some simple database entries
        FunctionalTest.setUp(self)