import unittest

class NLPSetupTests(unittest.TestCase):
    def test_spacy_installation(self):
        """Test if spaCy is properly installed"""
        import spacy # type: ignore
        nlp = spacy.load('en_core_web_sm')
        doc = nlp("Test sentence")
        self.assertTrue(len(doc) > 0)

    def test_nltk_installation(self):
        """Test if NLTK is properly installed"""
        import nltk # type: ignore
        from nltk.tokenize import word_tokenize # type: ignore
        nltk.download('punkt')
        tokens = word_tokenize("Test sentence")
        self.assertTrue(len(tokens) > 0)

if __name__ == '__main__':
    unittest.main()