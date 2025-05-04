from django.db.models import Q # type: ignore
from .models import Deduction, FAQStatic, TaxSlab, QualifyingPayment, TaxCalendar

class ResponseHandler:
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

    def get_faq_response(self, keywords):
        """Get response from FAQ table"""
        query = Q()
        for keyword in keywords:
            query |= Q(keywords__icontains=keyword)
            
        faq = FAQStatic.objects.filter(query).first()
        return faq.answer if faq else None

    def get_tax_slab_response(self):
        """Get tax slab information from database"""
        slabs = TaxSlab.objects.all().order_by('income_range_start')
        if not slabs.exists():
            return None
            
        response = "Tax Rates for Year 2025:\n\n"
        for slab in slabs:
            end_range = slab.income_range_end or "and above"
            response += (
                f"• Income Range: Rs. {slab.income_range_start:,} to "
                f"{end_range if isinstance(end_range, str) else f'Rs. {end_range:,}'}\n"
                f"  - Rate: {slab.tax_rate}%\n"
            )
        return response