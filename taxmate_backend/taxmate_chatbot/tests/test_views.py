from django.test import TestCase
from taxmate_chatbot.models import UserQuery

class UserQueryModelTest(TestCase):
    def test_question_field_exists(self):
        user_query = UserQuery(question="How to calculate tax?")
        self.assertTrue(hasattr(user_query, 'question'))

    def test_question_field_functionality(self):
        user_query = UserQuery(question="How to calculate tax?")
        self.assertEqual(user_query.question, "How to calculate tax?")