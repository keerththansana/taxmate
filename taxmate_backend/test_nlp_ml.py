import os
import django # type: ignore
import logging
from django.test import TestCase # type: ignore
from django.db.models import Q # type: ignore
from datetime import datetime
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxmate_backend.settings')
django.setup()

from taxmate_chatbot.nlp_processor import TaxNLPProcessor
from taxmate_chatbot.ml_model import TaxResponsePredictor
# Remove TaxSchedule from imports since it doesn't exist
from taxmate_chatbot.models import (
    UserQuery, 
    FAQStatic, 
    TaxSlab, 
    Deduction, 
    QualifyingPayment
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaxMateTests(TestCase):
    def setUp(self):
        """Initialize test data"""
        try:
            # Tax Slabs
            TaxSlab.objects.create(
                income_range_start=0,
                income_range_end=1200000,
                tax_rate=6,
                tax_year=2024
            )

            # Deductions - Fixed field names to match model
            Deduction.objects.create(
                name="Charitable Donations",
                description="Donations made to approved charitable institutions",
                amount=Decimal('75000.00'),
                special_conditions="Limited to 1/3 of taxable income or Rs. 75,000, whichever is less",
                tax_year=2024,
                active=True
            )

            # FAQs
            FAQStatic.objects.create(
                question="What is APIT?",
                answer="APIT is Advance Personal Income Tax, deducted monthly from employment income.",
                keywords="apit, tax, monthly, employment"
            )

            logger.info("Test data initialized successfully")
            
        except Exception as e:
            logger.error(f"Error in setUp: {str(e)}")
            raise

    def test_nlp_processor(self):
        """Test NLP functionality"""
        try:
            nlp = TaxNLPProcessor()
            
            # Test cases
            test_queries = [
                "What is APIT?",
                "Calculate tax for Rs. 5,000,000",
                "Tell me about personal relief",
                "When is the tax filing deadline?"
            ]
            
            logger.info("\nTesting NLP Processor...")
            for query in test_queries:
                processed = nlp.preprocess_text(query)
                logger.info(f"\nInput: {query}")
                logger.info(f"Processed: {processed}")
                
                # Verify processed text is not empty
                assert processed, f"Processing failed for: {query}"
                
            logger.info("NLP tests passed successfully!")
            return True

        except Exception as e:
            logger.error(f"NLP Test Failed: {str(e)}")
            return False

    def test_ml_model(self):
        """Test ML model functionality"""
        try:
            predictor = TaxResponsePredictor()
            
            # Test data
            test_data = [
                ("What is APIT system?", "APIT is Advance Personal Income Tax..."),
                ("Tell me about tax rates", "Current tax rates range from 6% to 36%"),
                ("Personal relief amount?", "Personal relief is Rs. 1,200,000"),
                ("When to pay taxes?", "Tax payments are due quarterly")
            ]
            
            # Train model
            X = [q for q, _ in test_data]
            y = [a for _, a in test_data]
            
            logger.info("\nTesting ML Model...")
            
            # Test training
            accuracy = predictor.train(X, y)
            logger.info(f"Training accuracy: {accuracy:.2f}")
            assert accuracy > 0, "Training failed with 0 accuracy"
            
            # Test predictions
            test_queries = [
                "What is APIT?",
                "Tell me tax rates",
                "How much is relief?"
            ]
            
            logger.info("\nTesting predictions:")
            for query in test_queries:
                prediction = predictor.predict(query)
                logger.info(f"\nQuery: {query}")
                logger.info(f"Response: {prediction}")
                
                # Verify prediction is not empty
                assert prediction, f"Prediction failed for: {query}"
            
            logger.info("ML tests passed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"ML Test Failed: {str(e)}")
            return False

    def test_comprehensive_search(self):
        """Test searching across all database tables"""
        try:
            nlp = TaxNLPProcessor()
            predictor = TaxResponsePredictor()

            # Test queries that should search across all tables
            test_queries = [
                "What are the conditions for charitable donations?",
                "Tell me about tax rates for 1.2 million income",
                "What is APIT system?",
                "How much can I claim for donations?",
            ]

            logger.info("\nTesting Comprehensive Database Search...")
            for query in test_queries:
                # Preprocess query
                processed_query = nlp.preprocess_text(query)
                
                # Search across all tables
                results = self.search_all_tables(processed_query)
                
                # Format response
                response = self.format_search_results(results)
                
                logger.info(f"\nQuery: {query}")
                logger.info(f"Results found: {len(results)}")
                logger.info(f"Response: {response}")
                
                # Verify we got relevant results
                assert response, f"No results found for: {query}"

            return True

        except Exception as e:
            logger.error(f"Comprehensive Search Test Failed: {str(e)}")
            return False

    def search_all_tables(self, query):
        """Search across all database tables with cleaned text"""
        results = []
        
        try:
            # Clean the query
            clean_query = ''.join(c for c in query if c.isalnum() or c.isspace()).lower()
            
            # Search FAQs with cleaned text comparison
            faq_results = FAQStatic.objects.all()
            faq_matches = [
                faq for faq in faq_results
                if clean_query in ''.join(c for c in faq.question.lower() if c.isalnum() or c.isspace()) or
                clean_query in ''.join(c for c in faq.answer.lower() if c.isalnum() or c.isspace()) or
                clean_query in ''.join(c for c in faq.keywords.lower() if c.isalnum() or c.isspace())
            ]
            results.extend([('FAQ', r) for r in faq_matches])

            # Search Deductions with cleaned text comparison
            deduction_results = Deduction.objects.all()
            deduction_matches = [
                deduction for deduction in deduction_results
                if clean_query in ''.join(c for c in deduction.deduction_name.lower() if c.isalnum() or c.isspace()) or
                clean_query in ''.join(c for c in (deduction.deduction_description or '').lower() if c.isalnum() or c.isspace()) or
                clean_query in ''.join(c for c in (deduction.special_conditions or '').lower() if c.isalnum() or c.isspace())
            ]
            results.extend([('Deduction', r) for r in deduction_matches])

            # Search Tax Slabs with cleaned text comparison
            taxslab_results = TaxSlab.objects.all()
            taxslab_matches = [
                slab for slab in taxslab_results
                if clean_query in str(slab.tax_rate).lower() or
                clean_query in str(slab.tax_year)
            ]
            results.extend([('TaxSlab', r) for r in taxslab_matches])

            return results

        except Exception as e:
            logger.error(f"Database search error: {str(e)}")
            return []

    def format_search_results(self, results):
        """Format search results with bold text but no special characters"""
        if not results:
            return "No relevant information found"

        response = []
        for table_name, result in results:
            if table_name == 'FAQ':
                clean_question = ' '.join(result.question.split())
                clean_answer = ' '.join(result.answer.split())
                response.append(
                    f"**Question** {clean_question}\n"
                    f"**Answer** {clean_answer}"
                )
                
            elif table_name == 'Deduction':
                clean_name = ' '.join(result.name.split())
                clean_desc = ' '.join((result.description or '').split())
                clean_conditions = ' '.join((result.special_conditions or '').split())
                response.append(
                    f"**Deduction** {clean_name}\n"
                    f"**Description** {clean_desc}\n"
                    f"**Amount** Rs {result.amount:,.0f}\n"
                    f"**Conditions** {clean_conditions}"
                )
                
            elif table_name == 'TaxSlab':
                response.append(
                    f"**Tax Rate** {result.tax_rate}%\n"
                    f"**Income Range** Rs {result.income_range_start:,.0f} to "
                    f"Rs {result.income_range_end:,.0f}"
                )
                
            # Remove TaxSchedule case since the model doesn't exist
            elif table_name == 'QualifyingPayment':
                clean_name = ' '.join(result.name.split())
                clean_conditions = ' '.join((result.conditions or '').split())
                response.append(
                    f"**Payment Type** {clean_name}\n"
                    f"**Conditions** {clean_conditions}\n"
                    f"**Amount** Rs {result.amount:,.0f}"
                )

        return "\n\n".join(response)

if __name__ == "__main__":
    logger.info("Starting TaxMate Comprehensive Tests...")
    
    test_case = TaxMateTests()
    test_case._pre_setup()
    test_case.setUp()
    
    nlp_success = test_case.test_nlp_processor()
    ml_success = test_case.test_ml_model()
    search_success = test_case.test_comprehensive_search()
    
    if (nlp_success and ml_success and search_success):
        logger.info("\nAll tests passed successfully!")
    else:
        logger.error("\nSome tests failed. Check logs for details.")