from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
import joblib
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

class TaxResponsePredictor:
    def __init__(self):
        """Initialize with NLTK components"""
        try:
            # Initialize NLTK components
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            
            # Initialize vectorizer with string stop_words parameter
            self.vectorizer = TfidfVectorizer(
                stop_words='english',  # Changed from set to string
                tokenizer=self._tokenize_text,
                ngram_range=(1, 2)
            )
            self.responses = []
            self.response_vectors = None
            logger.info("ML model initialized successfully")
        except Exception as e:
            logger.error(f"ML model initialization error: {str(e)}")
            raise

    def _tokenize_text(self, text):
        """Tokenize text using NLTK"""
        try:
            tokens = word_tokenize(text.lower())
            return [t for t in tokens if t.isalnum() and t not in self.stop_words]
        except Exception as e:
            logger.error(f"Tokenization error: {str(e)}")
            return text.lower().split()
        
    def train(self, X, y):
        """Train the model with question-answer pairs"""
        try:
            self.responses = y
            # Fit and transform the questions
            X_vectors = self.vectorizer.fit_transform(X)
            self.response_vectors = X_vectors
            
            # Calculate accuracy using cross-validation
            accuracy = self._calculate_accuracy(X)
            return accuracy
            
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            return 0.0
            
    def predict(self, query, threshold=0.3):
        """Predict response with similarity threshold"""
        try:
            if not self.response_vectors or not self.responses:
                return "Model not trained yet"
                
            # Transform query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.response_vectors).flatten()
            
            # Get best match above threshold
            best_idx = np.argmax(similarities)
            
            if similarities[best_idx] >= threshold:
                return self.responses[best_idx]
            else:
                return f"I'm not confident about this query (similarity: {similarities[best_idx]:.2f}). Please rephrase or be more specific."
                
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return "Error processing query"
            
    def _calculate_accuracy(self, X):
        """Calculate model accuracy using leave-one-out"""
        try:
            correct = 0
            total = len(X)
            
            for i in range(total):
                # Hold out one sample
                train_vectors = self.response_vectors[np.arange(total) != i]
                test_vector = self.response_vectors[i]
                
                # Calculate similarity
                similarities = cosine_similarity(test_vector, train_vectors).flatten()
                pred_idx = np.argmax(similarities)
                
                if similarities[pred_idx] >= 0.3:  # Using same threshold
                    correct += 1
                    
            return correct / total
            
        except Exception as e:
            logger.error(f"Accuracy calculation error: {str(e)}")
            return 0.0

    def save_model(self, filepath):
        """Save model to file"""
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'responses': self.responses,
                'response_vectors': self.response_vectors
            }
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise

    def load_model(self, filepath):
        """Load model from file"""
        try:
            model_data = joblib.load(filepath)
            self.vectorizer = model_data['vectorizer']
            self.responses = model_data['responses']
            self.response_vectors = model_data['response_vectors']
            logger.info(f"Model loaded from {filepath}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise