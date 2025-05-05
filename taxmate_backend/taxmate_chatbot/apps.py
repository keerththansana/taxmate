from django.apps import AppConfig # type: ignore
import logging
from django.conf import settings # type: ignore

logger = logging.getLogger(__name__)

class TaxmateChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'taxmate_chatbot'
    nlp = None  # Store NLP model instance

    def ready(self):
        """Initialize application resources and NLP components"""
        if settings.DEBUG:
            logger.info("Initializing TaxMate Chatbot in DEBUG mode")
        
        try:
            # Import here to avoid circular imports
            from .nlp_setup import setup_nlp
            
            # Initialize NLP components
            self.nlp = setup_nlp()
            logger.info("NLP components initialized successfully")
            
            # Verify model loaded correctly
            test_text = "Test sentence for NLP model."
            doc = self.nlp(test_text)
            if doc and len(doc) > 0:
                logger.info("NLP model verification successful")
            
        except ImportError as ie:
            logger.error(f"Failed to import NLP components: {str(ie)}")
            raise SystemExit("Critical: NLP components not available")
            
        except Exception as e:
            logger.error(f"NLP initialization failed: {str(e)}", exc_info=True)
            if settings.DEBUG:
                raise  # Re-raise in debug mode
            else:
                logger.warning("Continuing without NLP support - limited functionality")
        
        # Initialize other app resources
        self.setup_additional_resources()
    
    def setup_additional_resources(self):
        """Setup additional application resources"""
        try:
            # Initialize any other required resources
            pass
        except Exception as e:
            logger.error(f"Additional resource setup failed: {str(e)}")
