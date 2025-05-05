import logging
from django.db.models import Q
from .models import FAQStatic, Deduction, TaxSlab, TaxCalendar

logger = logging.getLogger(__name__)

class ResponseHandler:
    """Handles response formatting for the chatbot"""
    
    def format_heading(self, text):
        """Format heading with bold text"""
        return f"**{text}**"

    def format_tax_info(self, data):
        """Format tax information with proper headings"""
        sections = []
        
        # Format main heading
        if data.get('title'):
            sections.append(self.format_heading("Tax Information Results"))
            sections.append("")
        
        # Format deductions
        if data.get('deductions'):
            sections.append(self.format_heading("Tax Deductions"))
            sections.append("")
            for deduction in data['deductions']:
                sections.append(self.format_heading(deduction['type']))
                sections.append(deduction['description'])
                if deduction.get('details'):
                    sections.append("Details:")
                    for key, value in deduction['details'].items():
                        sections.append(f"- {key}: {value}")
                sections.append("")
        
        # Format calendar events
        if data.get('calendar'):
            sections.append(self.format_heading("Important Dates"))
            sections.append("Tax Calendar Events")
            sections.append("")
            for event in data['calendar']:
                sections.extend([
                    f"• {event['name']}",
                    f"  - Date: {event['date']}",
                    f"  - Description: {event['description']}",
                    f"  - Frequency: {event.get('frequency', '')}",
                    ""
                ])
        
        # Add help section
        sections.extend([
            self.format_heading("Need More Information?"),
            "",
            "Ask about:",
            "",
            "• Tax calculations",
            "• Available deductions",
            "• Payment deadlines",
            "• Documentation requirements"
        ])
        
        return "\n".join(sections)
    
    def get_response(self, intent, entities, keywords):
        """Get response from database based on intent and entities"""
        
        # Try FAQ static table first
        faq_response = self.get_faq_response(keywords)
        if faq_response:
            return faq_response
        
        # Try tax slabs for tax rate queries
        if intent == 'tax_rates':
            return self.get_tax_slab_response()
        
        # Try deductions table
        deduction_response = self.get_deduction_response(keywords)
        if deduction_response:
            return deduction_response
        
        # Try qualifying payments
        payment_response = self.get_qualifying_payment_response(keywords)
        if payment_response:
            return payment_response
        
        # Try tax calendar
        calendar_response = self.get_calendar_response(keywords)
        if calendar_response:
            return calendar_response
        
        return "I couldn't find relevant information for your query."

    @staticmethod
    def get_faq_response(query):
        """Get response from FAQ table"""
        try:
            faq = FAQStatic.objects.filter(
                Q(question__icontains=query) |
                Q(keywords__icontains=query)
            ).first()
            return faq.answer if faq else None
        except Exception as e:
            return None

    @staticmethod
    def get_deduction_response(query):
        """Get deduction related information"""
        try:
            deduction = Deduction.objects.filter(
                Q(deduction_type__icontains=query) |
                Q(description__icontains=query)
            ).first()
            if deduction:
                return {
                    'type': deduction.deduction_type,
                    'description': deduction.description,
                    'amount': deduction.max_allowable_amount,
                    'conditions': deduction.special_conditions
                }
            return None
        except Exception as e:
            return None

    @staticmethod
    def get_tax_slab_info():
        """Get current tax slab information"""
        try:
            slabs = TaxSlab.objects.all().order_by('income_range_start')
            if slabs.exists():
                return [{
                    'start': slab.income_range_start,
                    'end': slab.income_range_end,
                    'rate': slab.tax_rate
                } for slab in slabs]
            return None
        except Exception as e:
            return None

    def format_response(self, response_type, data):
        """Format response without markdown symbols"""
        try:
            if response_type == 'greeting':
                return data
                
            elif response_type == 'faq':
                return f"{data.question}\n\n{data.answer}"
                
            elif response_type == 'tax_slab':
                return (
                    f"Tax Slab Information\n"
                    f"Range: Rs. {data.income_range_start:,} to {data.income_range_end:,}\n"
                    f"Rate: {data.tax_rate}%"
                )
                
            elif response_type == 'deduction':
                response = [
                    f"Type: {data.deduction_type}",
                    f"Description: {data.description}"
                ]
                if data.max_allowable_amount:
                    response.append(f"Maximum Amount: Rs. {data.max_allowable_amount:,}")
                if data.special_conditions:
                    response.append(f"Conditions: {data.special_conditions}")
                return "\n".join(response)
                
            return str(data)
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return "Error formatting response"