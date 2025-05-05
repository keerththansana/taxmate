import spacy # type: ignore
import nltk # type: ignore
import logging

logger = logging.getLogger(__name__)

def setup_nlp():
    """Initialize NLP components"""
    try:
        # Download NLTK data
        nltk.download('punkt', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
        nltk.download('maxent_ne_chunker', quiet=True)
        nltk.download('words', quiet=True)
        
        # Load spaCy model
        nlp = spacy.load('en_core_web_sm')
        return nlp
    except Exception as e:
        logger.error(f"Error setting up NLP: {str(e)}")
        raise