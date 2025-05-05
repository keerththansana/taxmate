from django.test import TestCase # type: ignore
from django.db.models import Q # type: ignore
from .models import FAQStatic, TaxSlab, Deduction
from .views import ChatbotView

class ResponseTests(TestCase):
    def setUp(self):
        """Set up test data"""
        self.chatbot = ChatbotView()
        
        # Create test FAQ data
        self.faq = FAQStatic.objects.create(
            question="What is APIT?",
            answer="APIT (Advance Personal Income Tax) is a system where employers deduct income tax from employees' monthly salary. This helps spread the tax liability throughout the year instead of paying a lump sum.",
            keywords="apit,advance personal income tax,tax deduction"
        )
        
        # Create test tax slab data
        self.tax_slab = TaxSlab.objects.create(
            income_range_start=0,
            income_range_end=1200000,
            tax_rate=6,
            tax_year=2025
        )

    def test_faq_database_fetch(self):
        """Test if FAQ responses are fetched from database"""
        # Direct database query
        faq = FAQStatic.objects.filter(
            Q(question__icontains='apit') |
            Q(keywords__icontains='apit')
        ).first()
        
        self.assertIsNotNone(faq, "FAQ entry should exist in database")
        self.assertEqual(faq.question, "What is APIT?")
        self.assertIn("monthly salary", faq.answer)

        # Test through chatbot view
        response = self.chatbot.chat(type('Request', (), {'data': {'message': 'What is APIT?'}})())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn("APIT", response.data['response'])

    def test_missing_faq(self):
        """Test behavior when FAQ doesn't exist"""
        response = self.chatbot.chat(type('Request', (), {'data': {'message': 'What is XYZ?'}})())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertNotIn("XYZ", response.data['response'])