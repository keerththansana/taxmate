from django.test import TestCase
import spacy
import nltk
from nltk.tokenize import word_tokenize

class NLPSetupTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up NLP resources"""
        super().setUpClass()
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('maxent_ne_chunker')
        nltk.download('words')

    def test_nltk_installation(self):
        """Test if NLTK is properly installed"""
        try:
            tokens = word_tokenize("Test sentence")
            self.assertIsInstance(tokens, list)
            self.assertTrue(len(tokens) > 0)
        except LookupError as e:
            self.fail(f"NLTK resource not found: {str(e)}")

    def test_spacy_installation(self):
        """Test if spaCy is properly installed"""
        try:
            nlp = spacy.load('en_core_web_sm')
            doc = nlp("Test sentence")
            self.assertTrue(len(doc) > 0)
        except Exception as e:
            self.fail(f"spaCy model loading failed: {str(e)}")

if __name__ == '__main__':
    unittest.main()