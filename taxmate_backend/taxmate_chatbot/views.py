from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from .models import Deduction, FAQStatic, UserQuery, TaxSlab
from decimal import Decimal
import logging
import re

logger = logging.getLogger(__name__)

class ChatbotView(ViewSet):
    def get_tax_slab_info(self, income=None):
        """Get tax slab information from database"""
        try:
            slabs = TaxSlab.objects.all().order_by('income_range_start')
            if not slabs.exists():
                return "# ⚠️ No tax slab information available"

            response = "# 💰 Income Tax Slabs\n\n"
            for slab in slabs:
                end_range = slab.income_range_end or "and above"
                response += (
                    f"## Income Range: Rs. {slab.income_range_start:,} to "
                    f"{end_range if isinstance(end_range, str) else f'Rs. {end_range:,}'}\n"
                    f"- Tax Rate: **{slab.tax_rate}%**\n"
                    f"- Tax Year: {slab.tax_year}\n\n"
                )
            return response
        except Exception as e:
            logger.error(f"Error fetching tax slabs: {str(e)}")
            return "# ⚠️ Error fetching tax information"

    def calculate_tax(self, income):
        """Calculate tax using database tax slabs"""
        try:
            if not income or income <= 0:
                return "# ⚠️ Please provide a valid income amount"
            
            income = Decimal(str(income))
            tax_slabs = TaxSlab.objects.all().order_by('income_range_start')
            total_tax = Decimal('0')
            remaining_income = income
            calculation = "# 🧮 Tax Calculation\n\n"
            
            for slab in tax_slabs:
                if remaining_income <= 0:
                    break
                
                slab_limit = slab.income_range_end or Decimal('9999999999')
                taxable_in_slab = min(
                    remaining_income, 
                    slab_limit - slab.income_range_start
                )
                
                if taxable_in_slab > 0:
                    tax_in_slab = taxable_in_slab * Decimal(str(slab.tax_rate)) / Decimal('100')
                    total_tax += tax_in_slab
                    calculation += (
                        f"## Slab: Rs. {slab.income_range_start:,} to "
                        f"{slab.income_range_end or 'above'}\n"
                        f"- Taxable Amount: Rs. {taxable_in_slab:,.2f}\n"
                        f"- Rate: {slab.tax_rate}%\n"
                        f"- Tax: Rs. {tax_in_slab:,.2f}\n\n"
                    )
                    remaining_income -= taxable_in_slab
            
            calculation += f"# 💵 Total Tax Payable\nRs. {total_tax:,.2f}"
            return calculation

        except Exception as e:
            logger.error(f"Error calculating tax: {str(e)}")
            return "# ⚠️ Error calculating tax"

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

            response = "# 💰 Tax Deductions\n\n"
            for deduction in deductions:
                response += (
                    f"## {deduction.deduction_type}\n"
                    f"{deduction.description}\n\n"
                    f"### Details\n"
                    f"- Maximum Amount: Rs. {deduction.max_allowable_amount:,}\n"
                    f"- Rate: {deduction.percentage}%\n"
                    f"- Conditions: {deduction.special_conditions}\n\n"
                )
            return response

        except Exception as e:
            logger.error(f"Error fetching deductions: {str(e)}")
            return None

    @action(detail=False, methods=['POST'])
    def chat(self, request):
        try:
            user_message = request.data.get('message', '').lower().strip()
            logger.info(f"Processing query: {user_message}")

            if not user_message:
                return Response({
                    'success': True,
                    'response': "# ❓ Please ask a tax-related question"
                })

            # Extract keywords
            keywords = [word for word in user_message.split() 
                       if word not in {'what', 'is', 'are', 'how', 'much', 'the', 'for'}]

            # Check for tax calculation
            if any(word in user_message for word in ['calculate', 'compute']):
                income_match = re.search(r'(\d[\d,]*)', user_message)
                if income_match:
                    income = float(income_match.group(1).replace(',', ''))
                    return Response({
                        'success': True,
                        'response': self.calculate_tax(income)
                    })

            # Check for tax slabs
            if any(term in user_message for term in ['slab', 'rate', 'percentage']):
                return Response({
                    'success': True,
                    'response': self.get_tax_slab_info()
                })

            # Check for deductions
            deduction_info = self.get_deduction_info(keywords)
            if deduction_info:
                return Response({
                    'success': True,
                    'response': deduction_info
                })

            # Try FAQ matching
            faq = FAQStatic.objects.filter(
                Q(keywords__icontains=' '.join(keywords)) |
                Q(question__icontains=' '.join(keywords))
            ).first()

            if faq:
                return Response({
                    'success': True,
                    'response': f"# ❓ {faq.question}\n\n{faq.answer}"
                })

            # Store unmatched query
            UserQuery.objects.create(
                question=user_message,
                matched_response="No match found",
                conversation_id=request.session.session_key or 'default'
            )

            # Get available topics from database
            deduction_types = Deduction.objects.values_list('deduction_type', flat=True)
            
            return Response({
                'success': True,
                'response': (
                    "# 🤔 Available Tax Topics\n\n"
                    "## Deduction Types\n" +
                    "\n".join([f"- {dtype}" for dtype in deduction_types]) +
                    "\n\n## Example Queries\n"
                    "- Calculate tax for Rs. 2,500,000\n"
                    "- What are the current tax rates?\n"
                    "- Tell me about personal relief\n"
                    "- How does EPF deduction work?"
                )
            })

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'response': "# ⚠️ Error\nSorry, something went wrong. Please try again."
            }, status=500)
