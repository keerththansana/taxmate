from django.test import TestCase
from taxmate_chatbot.models import UserQuery

class UserQueryModelTest(TestCase):
    def setUp(self):
        self.user_query = UserQuery.objects.create(question="How to calculate tax?")

    def test_question_field_exists(self):
        self.assertTrue(hasattr(self.user_query, 'question'))

    def test_question_field_value(self):
        self.assertEqual(self.user_query.question, "How to calculate tax?")