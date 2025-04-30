from django.db.models import Q # type: ignore
from rest_framework.decorators import action # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.viewsets import ViewSet # type: ignore
from .models import Deduction, FAQStatic, UserQuery  # Add this line
import logging
import re

logger = logging.getLogger('taxmate_chatbot')

class ChatbotView(ViewSet):
    def format_deduction_response(self, deduction):
        """Format deduction details into markdown response"""
        response = f"# {deduction.deduction_type}\n\n"
        response += f"## Description\n{deduction.description}\n\n"
        
        if deduction.max_allowable_amount:
            response += f"## Maximum Amount\n**Rs. {deduction.max_allowable_amount:,.2f}**\n\n"
            
        if deduction.percentage:
            response += f"## Percentage\n**{deduction.percentage}%**\n\n"
            
        response += f"## Applicable To\n**{self.get_applicable_to_text(deduction.applicable_to)}**\n\n"
        
        if deduction.special_conditions:
            response += f"## Special Conditions\n{deduction.special_conditions}\n\n"
            
        return response

    def extract_keywords(self, text):
        """Extract relevant keywords from query"""
        # Remove common words and punctuation
        text = re.sub(r'[^\w\s]', '', text.lower())
        stop_words = {'what', 'is', 'are', 'how', 'does', 'do', 'the', 'for', 'to', 'in', 'a', 'an'}
        keywords = [word for word in text.split() if word not in stop_words]
        return keywords

    @action(detail=False, methods=['POST'])
    def chat(self, request):
        try:
            user_message = request.data.get('message', '').lower().strip()
            logger.info(f"Processing query: {user_message}")

            if not user_message:
                return Response({
                    'success': True,
                    'response': "# ❓ Please Ask a Question\nI can help you with tax-related information."
                })

            # Extract keywords from query
            keywords = self.extract_keywords(user_message)
            logger.info(f"Extracted keywords: {keywords}")

            # Define query patterns with weights
            patterns = {
                'personal_relief': {
                    'keywords': ['personal', 'relief', 'allowance', 'basic'],
                    'weight': 2,
                    'filters': Q(deduction_type__icontains='Personal Relief')
                },
                'rent': {
                    'keywords': ['rent', 'rental', 'house', 'property'],
                    'weight': 1.5,
                    'filters': Q(deduction_type__icontains='Rent')
                },
                'epf': {
                    'keywords': ['epf', 'provident', 'fund', 'retirement'],
                    'weight': 1.5,
                    'filters': Q(deduction_type__icontains='EPF')
                },
                'charitable': {
                    'keywords': ['charity', 'donation', 'charitable', 'donate'],
                    'weight': 1,
                    'filters': Q(deduction_type__icontains='Charitable')
                }
            }

            # Score each pattern
            pattern_scores = {}
            for category, config in patterns.items():
                score = sum(2 if kw in config['keywords'] else 1 
                          for kw in keywords if any(p in kw for p in config['keywords']))
                pattern_scores[category] = score * config['weight']

            # Get best matching pattern
            best_match = max(pattern_scores.items(), key=lambda x: x[1])
            if best_match[1] > 0:
                deduction = Deduction.objects.filter(
                    patterns[best_match[0]]['filters']
                ).first()
                if deduction:
                    return Response({
                        'success': True,
                        'response': self.format_deduction_response(deduction)
                    })

            # Try FAQ matching with keyword relevance
            matching_faqs = FAQStatic.objects.filter(
                Q(keywords__icontains=user_message) |
                Q(question__icontains=user_message)
            )
            
            if matching_faqs.exists():
                best_faq = max(matching_faqs, 
                    key=lambda faq: sum(kw in faq.keywords.lower() for kw in keywords))
                return Response({
                    'success': True,
                    'response': f"# ❓ {best_faq.question}\n\n{best_faq.answer}"
                })

            # Store query for training
            UserQuery.objects.create(
                question=user_message,
                matched_response="No match found",
                conversation_id=request.session.session_key or 'default'
            )

            # Return contextual suggestions
            return Response({
                'success': True,
                'response': self.get_contextual_suggestions(keywords)
            })

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'response': "# ⚠️ Error\nSorry, I encountered an error. Please try again."
            }, status=500)

    def get_contextual_suggestions(self, keywords):
        """Generate contextual suggestions based on keywords"""
        tax_terms = {'tax', 'income', 'payment'}
        relief_terms = {'relief', 'deduction', 'allowance'}
        
        if any(term in keywords for term in tax_terms):
            return (
                "# 📊 Tax Topics\n\n"
                "## Available Information\n"
                "- Income tax rates and slabs\n"
                "- Tax calculation methods\n"
                "- Tax payment calendar\n\n"
                "## Try Asking\n"
                "- 'What are the current tax rates?'\n"
                "- 'How is income tax calculated?'\n"
                "- 'When are tax payments due?'"
            )
        elif any(term in keywords for term in relief_terms):
            return (
                "# 💰 Tax Relief\n\n"
                "## Available Types\n"
                "- Personal Relief (Rs. 1,800,000)\n"
                "- Rent Relief\n"
                "- EPF Contributions\n"
                "- Charitable Donations\n\n"
                "## Try Asking\n"
                "- 'What is personal relief?'\n"
                "- 'How does rent relief work?'\n"
                "- 'Tell me about EPF deductions'"
            )
        else:
            return (
                "# 🤔 Need Help?\n\n"
                "## Popular Topics\n"
                "- Tax Calculations\n"
                "- Available Deductions\n"
                "- Payment Deadlines\n\n"
                "## Example Questions\n"
                "- 'What tax reliefs are available?'\n"
                "- 'How much is personal relief?'\n"
                "- 'When do I need to pay taxes?'"
            )
