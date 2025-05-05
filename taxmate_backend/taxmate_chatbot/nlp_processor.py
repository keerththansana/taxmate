import logging
import spacy # type: ignore
import nltk # type: ignore
from nltk.tokenize import word_tokenize # type: ignore
from nltk.corpus import stopwords # type: ignore
from nltk.sentiment import SentimentIntensityAnalyzer # type: ignore
try:
    from fuzzywuzzy import fuzz # type: ignore
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'fuzzywuzzy', 'python-Levenshtein'])
    from fuzzywuzzy import fuzz # type: ignore
from .response_handler import ResponseHandler

logger = logging.getLogger(__name__)

class TaxNLPProcessor:
    def __init__(self):
        """Initialize NLP components with error handling"""
        try:
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
            
            # Initialize NLTK components
            self.stop_words = set(stopwords.words('english'))
            self.sia = SentimentIntensityAnalyzer()
            self.response_handler = ResponseHandler()
            
            # Load spaCy model
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except OSError:
                logger.info("Downloading spaCy model...")
                spacy.cli.download('en_core_web_sm')
                self.nlp = spacy.load('en_core_web_sm')
            
            logger.info("NLP processor initialized successfully")
            
        except Exception as e:
            logger.error(f"NLP initialization error: {str(e)}")
            raise

    def analyze_sentiment(self, text):
        """Analyze sentiment of user message"""
        scores = self.sia.polarity_scores(text)
        return {
            'sentiment': 'positive' if scores['compound'] > 0.1 
                        else 'negative' if scores['compound'] < -0.1 
                        else 'neutral',
            'confidence': abs(scores['compound'])
        }

    def extract_conversation_context(self, text, previous_context=None):
        """Extract conversation context and maintain state"""
        doc = self.nlp(text.lower())
        context = {
            'intent': self.extract_intent(text),
            'sentiment': self.analyze_sentiment(text),
            'entities': self.extract_entities(text),
            'is_question': any(token.tag_ == 'WP' or token.tag_ == 'WRB' for token in doc),
            'conversation_type': self.get_conversation_type(text),
            'previous_context': previous_context
        }
        
        # Add topic continuity
        if previous_context and previous_context.get('topic'):
            if any(word in text.lower() for word in ['it', 'that', 'this', 'these']):
                context['topic'] = previous_context['topic']
        
        return context

    def get_conversation_type(self, text):
        """Determine type of conversation"""
        text_lower = text.lower()
        
        for pattern_type, patterns in self.conversation_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return pattern_type
        
        return 'general'

    def preprocess_text(self, text):
        """Preprocess input text"""
        try:
            # Tokenize and clean text
            doc = self.nlp(text.lower())
            tokens = [token.text for token in doc if not token.is_stop and token.is_alpha]
            return " ".join(tokens)
        except Exception as e:
            logger.error(f"Text preprocessing error: {str(e)}")
            return text

    def extract_intent(self, text):
        """Improved intent extraction with fuzzy matching and context"""
        try:
            text = text.lower()
            best_match = {'intent': 'general_query', 'score': 0}
            
            # Check for numbers and currency - likely calculation intent
            if any(char.isdigit() for char in text) and any(term in text for term in ['rs', 'rupees', 'lkr']):
                return 'calculation'
                
            # Check patterns
            for intent, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    # Exact match
                    if pattern in text:
                        return intent
                    
                    # Fuzzy match
                    score = fuzz.partial_ratio(pattern, text)
                    if score > best_match['score'] and score > 80:  # 80% threshold
                        best_match = {'intent': intent, 'score': score}
            
            # Log the intent detection
            logger.debug(f"Intent detected: {best_match['intent']} with score: {best_match['score']}")
            
            return best_match['intent']
            
        except Exception as e:
            logger.error(f"Error in intent extraction: {str(e)}")
            return 'general_query'

    def extract_entities(self, text):
        """Enhanced entity extraction"""
        try:
            doc = self.nlp(text)
            entities = {
                'amount': [],
                'date': [],
                'tax_type': [],
                'deduction_type': []
            }
            
            # Improved amount detection
            amount_patterns = [
                r'Rs\.?\s*[\d,]+',
                r'[\d,]+\s*rupees',
                r'[\d,]+\s*lkr'
            ]
            
            # Tax-specific terms
            tax_terms = {
                'tax_type': [
                    'income tax', 'apit', 'wht', 'vat', 'corporate tax',
                    'capital gains', 'withholding'
                ],
                'deduction_type': [
                    'relief', 'deduction', 'allowance', 'exemption',
                    'personal relief', 'rental', 'medical', 'donation'
                ]
            }
            
            # Process entities
            for ent in doc.ents:
                if ent.label_ == 'MONEY':
                    entities['amount'].append(ent.text)
                elif ent.label_ == 'DATE':
                    entities['date'].append(ent.text)
            
            # Check for tax-specific terms using fuzzy matching
            text_lower = text.lower()
            for category, terms in tax_terms.items():
                for term in terms:
                    if fuzz.partial_ratio(term, text_lower) > 80:
                        entities[category].append(term)
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {'amount': [], 'date': [], 'tax_type': [], 'deduction_type': []}