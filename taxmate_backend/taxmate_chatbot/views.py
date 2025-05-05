from django.db.models import Q # type: ignore
from rest_framework.decorators import action # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.viewsets import ViewSet # type: ignore
from fuzzywuzzy import fuzz # type: ignore
from .models import (
    Deduction, FAQStatic, UserQuery, TaxSlab,
    QualifyingPayment, TaxCalendar, GeneralResponse
)
from decimal import Decimal
import logging
import re
from .nlp_processor import TaxNLPProcessor
from .ml_model import TaxResponsePredictor

logger = logging.getLogger(__name__)

class ChatbotView(ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nlp_processor = TaxNLPProcessor()
        self.response_predictor = TaxResponsePredictor()
        
        # Initialize response templates
        self.response_templates = {
            'tax_info': """# Sri Lankan Tax Information

{content}

## Need help with:
• Tax Calculations
• Available Deductions
• Payment Deadlines
• Tax Filing""",
            
            'calculation': """# Tax Calculation Result

{content}

## Note:
This is a basic calculation. Actual tax may vary based on:
• Applicable deductions
• Special reliefs
• Qualifying payments""",
            
            'deduction': """# Available Tax Deductions

{content}

## Important:
• Keep all supporting documents
• Submit claims within deadline
• Verify eligibility criteria""",
            
            'error': """# ⚠️ Error

I apologize, but I encountered an issue while processing your request.
Please try:
• Rephrasing your question
• Being more specific
• Using example queries below

## Example Questions:
• "What is my tax for Rs. 2,500,000 income?"
• "Tell me about personal relief"
• "When is the tax filing deadline?"
"""
        }

    def train_model(self):
        """Train the ML model with existing queries"""
        queries = UserQuery.objects.all()
        if queries.exists():
            X = [q.question for q in queries]
            y = [q.matched_response for q in queries]
            self.response_predictor.train(X, y)

    def get_tax_slab_info(self, income=None):
        """Get tax slab information"""
        try:
            slabs = TaxSlab.objects.all().order_by('income_range_start')
            if not slabs.exists():
                return "Tax Information Not Available"

            response = "Income Tax Slabs\n\n"
            for slab in slabs:
                end_range = slab.income_range_end or "and above"
                response += (
                    f"• Income Range: Rs. {slab.income_range_start:,} to "
                    f"{end_range if isinstance(end_range, str) else f'Rs. {end_range:,}'}\n"
                    f"  - Tax Rate: {slab.tax_rate}%\n"
                    f"  - Tax Year: {slab.tax_year}\n\n"
                )
            return response
        except Exception as e:
            logger.error(f"Error fetching tax slabs: {str(e)}")
            return "Error fetching tax information"

    def calculate_tax(self, income_str):
        """Enhanced tax calculation with proper input handling"""
        try:
            # Clean and validate income input
            income_str = income_str.replace('Rs.', '').replace(',', '').strip()
            income = Decimal(income_str)
            
            if income <= 0:
                return "Please provide a valid positive income amount"

            # Get tax slabs in order
            tax_slabs = TaxSlab.objects.all().order_by('income_range_start')
            if not tax_slabs.exists():
                return "Tax slab information is not available"

            # Calculate tax with detailed breakdown
            total_tax = Decimal('0')
            remaining_income = income
            calculation_steps = []
            
            for slab in tax_slabs:
                if remaining_income <= 0:
                    break
                    
                slab_start = Decimal(str(slab.income_range_start))
                slab_end = Decimal(str(slab.income_range_end)) if slab.income_range_end else income
                slab_rate = Decimal(str(slab.tax_rate))
                
                # Calculate taxable amount in this slab
                taxable_in_slab = min(
                    remaining_income,
                    slab_end - slab_start
                )
                
                if taxable_in_slab > 0:
                    tax_in_slab = (taxable_in_slab * slab_rate) / Decimal('100')
                    total_tax += tax_in_slab
                    
                    # Format step details
                    step = {
                        'range': f"Rs. {slab_start:,} to {slab_end:,}",
                        'amount': f"Rs. {taxable_in_slab:,}",
                        'rate': f"{slab_rate}%",
                        'tax': f"Rs. {tax_in_slab:,.2f}"
                    }
                    calculation_steps.append(step)
                    remaining_income -= taxable_in_slab

            # Format response
            response = [
                "Tax Calculation Summary",
                f"Total Income: Rs. {income:,}",
                "\nBreakdown by Tax Slabs:"
            ]
            
            for step in calculation_steps:
                response.extend([
                    f"\nSlab: {step['range']}",
                    f"Taxable Amount: {step['amount']}",
                    f"Tax Rate: {step['rate']}",
                    f"Tax: {step['tax']}"
                ])
            
            response.extend([
                f"\nTotal Tax Payable: Rs. {total_tax:,.2f}",
                f"Effective Tax Rate: {(total_tax / income * 100):,.2f}%"
            ])
            
            return "\n".join(response)

        except ValueError as e:
            logger.error(f"Invalid income format: {str(e)}")
            return "Please provide a valid income amount (e.g., 5000000 or Rs. 5,000,000)"
        except Exception as e:
            logger.error(f"Tax calculation error: {str(e)}")
            return "Error calculating tax. Please try again."

    def get_deduction_info(self, keywords):
        """Fetch deduction information from database"""
        try:
            query = Q()
            for keyword in keywords:
                query |= (
                    Q(deduction_type__icontains=keyword) |
                    Q(description__icontains=keyword)
                )
            
            deductions = Deduction.objects.filter(query)
            if not deductions.exists():
                return None

            response = "# Tax Deductions\n\n"
            for deduction in deductions:
                response += f"## {deduction.deduction_type}\n"
                if deduction.description:
                    response += f"{deduction.description}\n\n"
                
                response += "### Details\n"
                if deduction.max_allowable_amount is not None:
                    response += f"- Maximum Amount: Rs. {deduction.max_allowable_amount:,}\n"
                if deduction.percentage is not None:
                    response += f"- Rate: {deduction.percentage}%\n"
                if deduction.special_conditions:
                    response += f"- Conditions: {deduction.special_conditions}\n"
                response += "\n"
            
            return response

        except Exception as e:
            logger.error(f"Error fetching deductions: {str(e)}")
            return "# ⚠️ Error\nUnable to fetch deduction information."

    def get_qualifying_payments_info(self, keywords):
        """Fetch qualifying payments information"""
        try:
            query = Q()
            for keyword in keywords:
                query |= (
                    Q(payment_type__icontains=keyword) |
                    Q(description__icontains=keyword)
                )
            
            payments = QualifyingPayment.objects.filter(query)
            if not payments.exists():
                return None

            response = "Qualifying Payments\n\n"
            for payment in payments:
                response += (
                    f"• {payment.payment_type}\n"
                    f"  - Description: {payment.description}\n"
                    f"  - Maximum Limit: Rs. {payment.max_limit:,}\n"
                    f"  - Tax Year: {payment.tax_year}\n\n"
                )
            return response
        except Exception as e:
            logger.error(f"Error fetching qualifying payments: {str(e)}")
            return None

    def get_tax_calendar_info(self, keywords):
        """Fetch tax calendar information"""
        try:
            query = Q()
            for keyword in keywords:
                query |= (
                    Q(event_name__icontains=keyword) |
                    Q(event_description__icontains=keyword)
                )
            
            events = TaxCalendar.objects.filter(query).order_by('event_date')
            if not events.exists():
                return None

            response = "Tax Calendar Events\n\n"
            for event in events:
                response += (
                    f"• {event.event_name}\n"
                    f"  - Date: {event.event_date.strftime('%B %d, %Y')}\n"
                    f"  - Description: {event.event_description}\n"
                    f"  - Frequency: {event.frequency}\n\n"
                )
            return response
        except Exception as e:
            logger.error(f"Error fetching tax calendar: {str(e)}")
            return None

    def get_general_response(self, text):
        """Get response for general conversation"""
        try:
            response = GeneralResponse.objects.filter(
                input_text__iexact=text.lower()
            ).first()
            
            if response:
                return response.response_text
            return None
        except Exception as e:
            logger.error(f"Error fetching general response: {str(e)}")
            return None

    def get_faq_info(self, keywords):
        """Get FAQ information with fuzzy matching"""
        try:
            best_match = {'faq': None, 'score': 0}
            
            # Get all FAQs
            faqs = FAQStatic.objects.all()
            search_text = ' '.join(keywords)
            
            for faq in faqs:
                # Check question similarity
                question_score = fuzz.partial_ratio(search_text.lower(), faq.question.lower())
                keyword_score = fuzz.partial_ratio(search_text.lower(), faq.keywords.lower())
                
                # Take best match score
                max_score = max(question_score, keyword_score)
                if max_score > best_match['score'] and max_score > 70:  # 70% threshold
                    best_match = {'faq': faq, 'score': max_score}
            
            if best_match['faq']:
                return (
                    f"Question: {best_match['faq'].question}\n"
                    f"Answer: {best_match['faq'].answer}\n"
                    f"Match Confidence: {best_match['score']}%"
                )
            return None
            
        except Exception as e:
            logger.error(f"Error fetching FAQ: {str(e)}")
            return None

    @action(detail=False, methods=['POST'])
    def chat(self, request):
        """Main chat endpoint with improved response handling"""
        try:
            user_message = request.data.get('message', '').strip()
            logger.info(f"Received message: {user_message}")

            # 1. First check for general responses (greetings, thanks, etc.)
            message_lower = user_message.lower()
            
            # Handle greetings
            if any(greeting in message_lower for greeting in ['hi', 'hello', 'good morning', 'good afternoon', 'good evening']):
                greeting_response = {
                    'hi': 'Hi! How can I help you with tax-related questions?',
                    'hello': 'Hello! I\'m here to assist you with tax information.',
                    'good morning': 'Good morning! How may I assist you today?',
                    'good afternoon': 'Good afternoon! What tax information do you need?',
                    'good evening': 'Good evening! How can I help you?'
                }
                
                # Find the most appropriate greeting
                for greeting in greeting_response:
                    if greeting in message_lower:
                        return Response({
                            'success': True,
                            'response': greeting_response[greeting]
                        })
                # Default greeting if no exact match
                return Response({
                    'success': True,
                    'response': greeting_response['hi']
                })

            # Handle thanks/farewell
            if any(word in message_lower for word in ['thank', 'thanks', 'bye', 'goodbye']):
                farewell_response = {
                    'thank': "You're welcome! Let me know if you need anything else.",
                    'thanks': "You're welcome! Have a great day!",
                    'bye': 'Goodbye! Have a great day!',
                    'goodbye': 'Goodbye! Feel free to return if you have more questions.'
                }
                
                # Find the most appropriate response
                for word in farewell_response:
                    if word in message_lower:
                        return Response({
                            'success': True,
                            'response': farewell_response[word]
                        })

            # Handle tax calculations
            if any(word in message_lower for word in ['calculate', 'tax for', 'income']):
                income_str = self.extract_income_amount(user_message)
                if income_str:
                    calculation = self.calculate_tax(income_str)
                    return Response({
                        'success': True,
                        'response': calculation
                    })
                else:
                    return Response({
                        'success': True,
                        'response': """Tax Calculation Help

Please provide your income in one of these formats:
• "Calculate tax for Rs. 5,000,000"
• "What is my tax for 5000000"
• "Tax calculation for Rs. 2,500,000"

Example: "Calculate tax for Rs. 5,000,000" """
                    })

            # Continue with existing tax-related query handling
            # Initialize response components
            responses = []
            found_match = False

            # 1. Check for specific database queries
            if 'personal relief' in user_message.lower():
                # Get specific personal relief information
                relief = Deduction.objects.filter(
                    deduction_type__icontains='personal relief'
                ).first()
                
                if relief:
                    response = [
                        "Personal Relief Information",
                        f"Amount: Rs. {relief.max_allowable_amount:,}",
                        f"Description: {relief.description}",
                    ]
                    if relief.special_conditions:
                        response.append(f"Conditions: {relief.special_conditions}")
                    responses.append("\n".join(response))
                    found_match = True

            elif 'apit' in user_message.lower():
                # Get specific APIT information
                apit_info = FAQStatic.objects.filter(
                    Q(question__icontains='apit') |
                    Q(keywords__icontains='apit')
                ).first()
                
                if apit_info:
                    responses.append(f"APIT Information\n{apit_info.answer}")
                    found_match = True

            elif any(term in user_message.lower() for term in ['tax rate', 'tax slab']):
                # Get specific tax slab information
                if 'first' in user_message.lower():
                    slab = TaxSlab.objects.order_by('income_range_start').first()
                    if slab:
                        responses.append(
                            f"First Tax Slab\n"
                            f"Range: Rs. {slab.income_range_start:,} to {slab.income_range_end:,}\n"
                            f"Rate: {slab.tax_rate}%"
                        )
                        found_match = True
                else:
                    slabs = TaxSlab.objects.all().order_by('income_range_start')
                    for slab in slabs:
                        if str(slab.tax_rate) in user_message:
                            responses.append(
                                f"Tax Slab Information\n"
                                f"Rate: {slab.tax_rate}%\n"
                                f"Range: Rs. {slab.income_range_start:,} to "
                                f"{slab.income_range_end or 'above'}"
                            )
                            found_match = True
                            break

            elif 'qualifying payment' in user_message.lower():
                # Get specific qualifying payment information
                payments = QualifyingPayment.objects.filter(
                    Q(payment_type__icontains=user_message) |
                    Q(description__icontains=user_message)
                )
                if payments.exists():
                    payment_info = "\n\n".join([
                        f"Payment: {p.payment_type}\n"
                        f"Description: {p.description}\n"
                        f"Maximum Limit: Rs. {p.max_limit:,}"
                        for p in payments
                    ])
                    responses.append(f"Qualifying Payments Information\n\n{payment_info}")
                    found_match = True

            elif 'deadline' in user_message.lower():
                # Get specific deadline information
                events = TaxCalendar.objects.filter(
                    Q(event_name__icontains=user_message) |
                    Q(event_description__icontains=user_message)
                ).order_by('event_date')
                
                if events.exists():
                    event_info = "\n\n".join([
                        f"Event: {e.event_name}\n"
                        f"Date: {e.event_date.strftime('%B %d, %Y')}\n"
                        f"Details: {e.event_description}"
                        for e in events
                    ])
                    responses.append(f"Tax Calendar Information\n\n{event_info}")
                    found_match = True

            # Return found responses
            if found_match:
                final_response = "\n\n".join(responses)
                
                # Store successful query
                UserQuery.objects.create(
                    question=user_message,
                    matched_response=final_response,
                    conversation_id=request.session.get('conversation_id', 'default')
                )
                
                return Response({
                    'success': True,
                    'response': final_response
                })

            # If no specific match found, try general query handling
            return self.handle_general_query(user_message, {})

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return Response({
                'success': False,
                'response': "Error\n\nI encountered an issue. Please try rephrasing your question."
            })

    def handle_greeting(self, message):
        """Handle greeting messages"""
        greetings = {
            'hi': 'Hi! How can I help you with tax-related questions?',
            'hello': "Hello! I'm here to assist you with tax information.",
            'good morning': 'Good morning! How may I assist you today?',
            'good afternoon': 'Good afternoon! What tax information do you need?',
            'good evening': 'Good evening! How can I help you?'
        }
        
        message = message.lower()
        response = greetings.get(message, greetings['hi'])
        
        return Response({
            'success': True,
            'response': response
        })

    def handle_farewell(self, message):
        """Handle farewell messages"""
        farewells = {
            'bye': 'Goodbye! Have a great day!',
            'goodbye': 'Goodbye! Feel free to return if you have more questions.',
            'thank you': "You're welcome! Let me know if you need anything else.",
            'thanks': "You're welcome! Have a great day!"
        }
        
        message = message.lower()
        response = farewells.get(message, farewells['bye'])
        
        return Response({
            'success': True,
            'response': response
        })

    def handle_calculation(self, entities):
        """Handle tax calculation requests"""
        try:
            amount = None
            if entities['amount']:
                # Extract numerical value from amount string
                amount_str = entities['amount'][0].replace('Rs.', '').replace(',', '')
                amount = float(amount_str)
            
            if amount:
                return Response({
                    'success': True,
                    'response': self.calculate_tax(amount)
                })
            
            return Response({
                'success': False,
                'response': 'Please specify an income amount for calculation.'
            })
            
        except Exception as e:
            logger.error(f"Error in calculation handler: {str(e)}")
            return Response({
                'success': False,
                'response': 'Sorry, I had trouble calculating the tax. Please try again.'
            })

    def handle_general_query(self, processed_text, entities):
        """Intelligent handling of tax-related queries with context awareness"""
        try:
            responses = []
            keywords = processed_text.split()
            
            # Check for specific query types
            if 'apit' in processed_text.lower():
                apit_info = FAQStatic.objects.filter(
                    Q(keywords__icontains='apit') |
                    Q(question__icontains='apit')
                ).first()
                if apit_info:
                    responses.append(f"## APIT System\n{apit_info.answer}")

            # Search Deductions
            deduction_info = self.get_deduction_info(keywords)
            if deduction_info:
                responses.append(deduction_info)

            # Search Tax Calendar
            calendar_info = self.get_tax_calendar_info(keywords)
            if calendar_info:
                responses.append(f"## Important Dates\n{calendar_info}")

            # Search Tax Slabs
            if any(term in processed_text.lower() for term in ['rate', 'slab', 'percentage']):
                slab_info = self.get_tax_slab_info()
                if slab_info:
                    responses.append(f"## Tax Rates\n{slab_info}")

            # If we have specific responses, return them
            if responses:
                return Response({
                    'success': True,
                    'response': "\n\n".join([
                        "# Tax Information Results",
                        *responses,
                        "\n## Need More Information?",
                        "Ask about:",
                        "• Tax calculations",
                        "• Available deductions",
                        "• Payment deadlines",
                        "• Documentation requirements"
                    ])
                })

            # Return default helpful response
            return Response({
                'success': True,
                'response': """# Tax Assistant

I understand you're asking about taxes. Here are some topics I can help with:

## Available Topics
1. Income Tax
   • Current tax rates
   • Personal income tax
   • APIT system

2. Deductions & Relief
   • Personal relief
   • Qualifying payments
   • Available deductions

3. Important Information
   • Filing deadlines
   • Payment methods
   • Documentation

## Example Questions
• "What is my tax for Rs. 2,500,000?"
• "Explain APIT system"
• "What deductions can I claim?"
• "When is the filing deadline?"

_Choose a topic or ask a specific question_"""
            })

        except Exception as e:
            logger.error(f"Error in general query handler: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'response': """# ⚠️ Error

I apologize, but I encountered an error. Please try:
• Rephrasing your question
• Being more specific
• Using simpler terms"""
            })

    def handle_confusion(self, context):
        """Handle user confusion with helpful responses"""
        return Response({
            'success': True,
            'response': "\n".join([
                "# Let Me Help You",
                "",
                "I notice you might be unclear about something. Let me help:",
                "",
                "## Common Topics",
                "1. Basic Tax Concepts",
                "   - Income Tax explained",
                "   - APIT system",
                "   - Tax rates and slabs",
                "",
                "2. Practical Information",
                "   - How to calculate your tax",
                "   - Available deductions",
                "   - Payment methods",
                "",
                "What would you like to know more about?"
            ])
        })

    def get_related_topics(self, context):
        """Generate related topics based on conversation context"""
        topics = []
        
        if 'tax_type' in context['entities']:
            topics.extend([
                "- Related tax rates and slabs",
                "- Available deductions",
                "- Payment deadlines"
            ])
        
        if 'deduction_type' in context['entities']:
            topics.extend([
                "- Other available deductions",
                "- Documentation requirements",
                "- Qualifying payments"
            ])
        
        if 'amount' in context['entities']:
            topics.extend([
                "- Tax saving opportunities",
                "- Payment schedules",
                "- APIT calculations"
            ])
        
        return "\n".join(topics) if topics else "No related topics found"

    def handle_tax_query(self, message, context):
        """Database-driven tax query handler"""
        try:
            # Preprocess and extract search terms
            search_terms = self.nlp_processor.preprocess_text(message).split()
            responses = []

            # 1. Direct Database Queries
            if 'apit' in message.lower():
                apit_faqs = FAQStatic.objects.filter(
                    Q(keywords__icontains='apit') | 
                    Q(question__icontains='apit')
                ).first()
                if apit_faqs:
                    responses.append(f"# APIT Information\n\n{apit_faqs.answer}")

            if any(word in message.lower() for word in ['rate', 'slab', 'tax']):
                slabs = TaxSlab.objects.filter(is_active=True).order_by('income_range_start')
                if slabs.exists():
                    slab_info = "\n".join([
                        f"• Rs. {s.income_range_start:,} to {s.income_range_end or 'Above'}: {s.tax_rate}%"
                        for s in slabs
                    ])
                    responses.append(f"# Current Tax Rates\n\n{slab_info}")

            if any(word in message.lower() for word in ['deduct', 'relief', 'allowance']):
                deductions = Deduction.objects.filter(is_active=True)
                if deductions.exists():
                    deduction_info = "\n".join([
                        f"## {d.deduction_type}\n{d.description}\n- Maximum: Rs. {d.max_allowable_amount:,}"
                        for d in deductions
                    ])
                    responses.append(f"# Available Deductions\n\n{deduction_info}")

            if any(word in message.lower() for word in ['deadline', 'date', 'when', 'due']):
                events = TaxCalendar.objects.filter(event_date__gte=timezone.now()).order_by('event_date')[:3] # type: ignore
                if events.exists():
                    calendar_info = "\n".join([
                        f"• {e.event_name}: {e.event_date.strftime('%B %d, %Y')}\n  {e.event_description}"
                        for e in events
                    ])
                    responses.append(f"# Upcoming Tax Deadlines\n\n{calendar_info}")

            if any(word in message.lower() for word in ['payment', 'qualify', 'donate']):
                payments = QualifyingPayment.objects.filter(is_active=True)
                if payments.exists():
                    payment_info = "\n".join([
                        f"## {p.payment_type}\n{p.description}\n- Limit: Rs. {p.max_limit:,}"
                        for p in payments
                    ])
                    responses.append(f"# Qualifying Payments\n\n{payment_info}")

            # If matches found, return formatted response
            if responses:
                response_text = "\n\n".join(responses)
                
                # Store successful query
                UserQuery.objects.create(
                    question=message,
                    matched_response=response_text,
                    confidence_score=90 if len(responses) > 1 else 70
                )
                
                return Response({
                    'success': True,
                    'response': response_text
                })

            # Try fuzzy matching if no exact matches
            best_match = self.get_faq_info(search_terms)
            if best_match:
                return Response({
                    'success': True,
                    'response': best_match
                })

            # No matches found - provide helpful suggestions
            return Response({
                'success': True,
                'response': """# Tax Information

I couldn't find specific information for your query. Here are some popular topics:

## Available Information
1. Income Tax
   • "What are the current tax rates?"
   • "How is income tax calculated?"

2. APIT System
   • "Explain APIT calculation"
   • "Monthly tax deduction process"

3. Deductions & Relief
   • "List available deductions"
   • "Personal relief amount"

4. Tax Calendar
   • "Payment deadlines"
   • "Filing dates"

_Try asking one of these specific questions_"""
            })

        except Exception as e:
            logger.error(f"Error in tax query handler: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'response': "# ⚠️ Error\n\nI encountered an error. Please try a simpler question."
            })

    def extract_income_amount(self, message):
        """Extract income amount from message"""
        try:
            # Match patterns like "Rs. 5,000,000" or "5000000"
            amount_pattern = r'Rs\.?\s*([\d,]+)'
            amount_match = re.search(amount_pattern, message)
            
            if amount_match:
                # Clean the amount string
                amount_str = amount_match.group(1).replace(',', '')
                return amount_str
            
            # Try to find plain numbers
            number_pattern = r'\b(\d+)\b'
            number_match = re.search(number_pattern, message)
            
            if number_match:
                return number_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting income: {str(e)}")
            return None

# In Django shell
from taxmate_chatbot.models import UserQuery
from taxmate_chatbot.ml_model import TaxResponsePredictor

queries = UserQuery.objects.all()
X = [q.question for q in queries]
y = [q.matched_response for q in queries]

predictor = TaxResponsePredictor()
accuracy = predictor.train(X, y)
predictor.save_model('tax_response_model.joblib')

