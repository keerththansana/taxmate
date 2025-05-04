from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
import joblib

class TaxResponsePredictor:
    def __init__(self):
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english')),
            ('clf', MultinomialNB())
        ])
        
    def train(self, queries, responses):
        """Train the model on historical queries"""
        X_train, X_test, y_train, y_test = train_test_split(
            queries, responses, test_size=0.2
        )
        
        self.model.fit(X_train, y_train)
        return self.model.score(X_test, y_test)
        
    def predict(self, query):
        """Predict most likely response category"""
        return self.model.predict([query])[0]
        
    def save_model(self, filepath):
        """Save trained model"""
        joblib.dump(self.model, filepath)
        
    def load_model(self, filepath):
        """Load trained model"""
        self.model = joblib.load(filepath)