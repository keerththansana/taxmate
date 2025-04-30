from rest_framework.viewsets import ViewSet # type: ignore
from rest_framework.decorators import action # type: ignore
from rest_framework.response import Response # type: ignore
from django.db.models import Q # type: ignore
from .models import Deduction, FAQStatic, UserQuery
import logging

logger = logging.getLogger('taxmate_chatbot')

class ChatbotView(ViewSet):
    def get_deduction_by_type(self, deduction_type):
        """Helper method to get deduction by type"""
        return Deduction.objects.filter(
            deduction_type__icontains=deduction_type
        ).first()

    def format_deduction_response(self, deduction):
        """Format deduction response with proper markdown"""
        if not deduction:
            return None

        response = f"# 💎 {deduction.deduction_type}\n\n"
        response += f"## Description\n{deduction.description}\n\n"
        
        if deduction.max_allowable_amount:
            response += f"## 💰 Maximum Amount\nRs. {float(deduction.max_allowable_amount):,.2f}\n\n"
        
        if deduction.percentage:
            response += f"## Percentage\n{deduction.percentage}%\n\n"
        
        response += f"## ✅ Eligibility\n"
        response += f"Applicable to: **{self.get_applicable_to_text(deduction.applicable_to)}**\n\n"
        
        if deduction.special_conditions:
            response += f"## ⚠️ Special Conditions\n{deduction.special_conditions}\n"

        return response

    @action(detail=False, methods=['POST'])
    def chat(self, request):
        try:
            user_message = request.data.get('message', '').lower().strip()
            logger.info(f"Processing query: {user_message}")

            if not user_message:
                return Response({
                    'success': True,
                    'response': "Please ask a specific question about taxes, deductions, or relief."
                })

            # Try exact matches first
            direct_match = Deduction.objects.filter(
                Q(deduction_type__iexact=user_message) |
                Q(deduction_type__icontains=user_message)
            ).first()

            if direct_match:
                logger.info(f"Found exact match: {direct_match.deduction_type}")
                return Response({
                    'success': True,
                    'response': self.format_deduction_response(direct_match)
                })

            # Try keyword matching
            keywords = {
                'personal relief': ['personal relief', 'relief', 'personal tax relief'],
                'rent relief': ['rent relief', 'rental', 'house rent'],
                'epf': ['epf', 'provident fund', 'retirement'],
                'solar': ['solar', 'renewable', 'panel'],
                'charitable': ['charity', 'donation', 'charitable']
            }

            for deduction_type, search_terms in keywords.items():
                if any(term in user_message for term in search_terms):
                    deduction = Deduction.objects.filter(
                        deduction_type__icontains=deduction_type
                    ).first()
                    if deduction:
                        logger.info(f"Found keyword match: {deduction.deduction_type}")
                        return Response({
                            'success': True,
                            'response': self.format_deduction_response(deduction)
                        })

            # Try FAQ matching
            faq = FAQStatic.objects.filter(
                Q(keywords__icontains=user_message) |
                Q(question__icontains=user_message)
            ).first()

            if faq:
                logger.info(f"Found FAQ match: {faq.question}")
                return Response({
                    'success': True,
                    'response': f"# ❓ {faq.question}\n\n{faq.answer}"
                })

            # Log unmatched query
            UserQuery.objects.create(
                question=user_message,
                matched_response="No match found",
                conversation_id='default'
            )

            # Return helpful suggestions
            return Response({
                'success': True,
                'response': (
                    "# 🤔 Available Tax Deductions\n\n"
                    "You can ask about:\n"
                    "- Personal Relief (Rs. 1,800,000)\n"
                    "- Rent Relief (25% of rental income)\n"
                    "- EPF Contributions (8%)\n"
                    "- Solar Panel Installation (Rs. 600,000)\n"
                    "- Charitable Donations (Rs. 75,000)\n\n"
                    "Try asking: 'What is personal relief?'"
                )
            })

        except Exception as e:
            logger.error(f"Error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'response': "Sorry, I encountered an error. Please try again."
            }, status=500)
