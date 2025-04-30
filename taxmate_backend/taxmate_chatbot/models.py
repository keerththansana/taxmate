from django.db import models # type: ignore

# Choice Fields
class PeriodChoices(models.TextChoices):
    MONTHLY = 'Monthly', 'Monthly'
    QUARTERLY = 'Quarterly', 'Quarterly'
    ANNUAL = 'Annual', 'Annual'

class RateTypeChoices(models.TextChoices):
    FIXED = 'Fixed', 'Fixed'
    SLAB = 'Slab', 'Slab'

class FrequencyChoices(models.TextChoices):
    YEARLY = 'Yearly', 'Yearly'
    QUARTERLY = 'Quarterly', 'Quarterly'

class AudienceChoices(models.TextChoices):
    INDIVIDUAL = 'Individual', 'Individual'
    ALL = 'All', 'All'

class IncomeTypeChoices(models.TextChoices):
    ALL = '1', 'All income types'
    EMPLOYMENT = '2', 'Employment income'
    RENTAL = '3', 'Rental income'
    INTEREST = '4', 'Interest income'
    BUSINESS = '5', 'Business income'

# 1. FAQ Static
class FAQStatic(models.Model):
    question = models.TextField()
    answer = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords")
    category = models.CharField(max_length=50)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question[:50]

# 2. Tax Slabs
class TaxSlab(models.Model):
    period = models.CharField(
        max_length=10, 
        choices=PeriodChoices.choices,
        default=PeriodChoices.ANNUAL
    )
    income_range_start = models.DecimalField(max_digits=12, decimal_places=2)
    income_range_end = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_year = models.IntegerField()

    class Meta:
        ordering = ['income_range_start']

# 3. Income Types
class IncomeType(models.Model):
    type_name = models.CharField(max_length=100)
    description = models.TextField()
    is_periodic = models.BooleanField(default=True)
    related_deductions = models.TextField(help_text="Comma-separated deduction codes or JSON")

    def __str__(self):
        return self.type_name

# 4. Income Subtypes
class IncomeSubtype(models.Model):
    income_type = models.ForeignKey(IncomeType, on_delete=models.CASCADE)
    subtype_name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.subtype_name

# 5. Deductions
class Deduction(models.Model):
    deduction_type = models.CharField(max_length=100)
    description = models.TextField()
    max_allowable_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tax_year = models.IntegerField()
    applicable_to = models.CharField(max_length=2, choices=IncomeTypeChoices.choices, default=IncomeTypeChoices.ALL)
    special_conditions = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.deduction_type

    def get_formatted_details(self):
        """Get formatted details for chatbot response"""
        details = {
            'type': self.deduction_type,
            'description': self.description,
            'amount': self.max_allowable_amount,
            'percentage': self.percentage,
            'applicable_to': self.get_applicable_to_display(),
            'conditions': self.special_conditions
        }
        return details

    def matches_query(self, query):
        """Check if deduction matches search query"""
        query = query.lower()
        return (
            query in self.deduction_type.lower() or
            query in self.description.lower() or
            (self.special_conditions and query in self.special_conditions.lower())
        )

# 6. Tax Rates by Income Subtype
class TaxRateByType(models.Model):
    income_subtype = models.ForeignKey(IncomeSubtype, on_delete=models.CASCADE)
    rate_type = models.CharField(max_length=10, choices=RateTypeChoices.choices)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    use_slabs = models.BooleanField(default=False)

# 7. Qualifying Payments
class QualifyingPayment(models.Model):
    payment_type = models.CharField(max_length=200)
    description = models.TextField()
    max_limit = models.DecimalField(max_digits=12, decimal_places=2)
    tax_year = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'taxmate_chatbot_qualifyingpayment'

    def __str__(self):
        return f"{self.payment_type} ({self.tax_year})"

    def to_dict(self):
        return {
            'id': self.id,
            'payment_type': self.payment_type,
            'description': self.description,
            'max_limit': float(self.max_limit),
            'tax_year': self.tax_year,
            'last_updated': self.last_updated.isoformat()
        }

# 8. Terminal Benefits
class TerminalBenefit(models.Model):
    benefit_type = models.CharField(max_length=100)
    description = models.TextField()
    exempted_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_exempted_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.benefit_type

# 9. Tax Calendar
class TaxCalendar(models.Model):
    event_name = models.CharField(max_length=200)
    event_description = models.TextField()
    event_date = models.DateField()
    frequency = models.CharField(max_length=10, choices=FrequencyChoices.choices)
    target_audience = models.CharField(max_length=20, choices=AudienceChoices.choices)

    def __str__(self):
        return self.event_name

# 10. User Queries (for ML)
class UserQuery(models.Model):
    question = models.TextField()
    matched_response = models.TextField()
    conversation_id = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_feedback = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_queries'

    def __str__(self):
        return f"{self.question[:50]}..."
