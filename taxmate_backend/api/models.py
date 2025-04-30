from django.db import models # type: ignore
from django.core.validators import MinValueValidator, MaxValueValidator # type: ignore

class TaxPayer(models.Model):
    TAX_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('head_of_household', 'Head of Household')
    ]

    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    nic = models.CharField(max_length=12, unique=True, db_index=True)
    date_of_birth = models.DateField()
    tax_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'taxpayers'
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['nic']),
            models.Index(fields=['email'])
        ]

class Income(models.Model):
    INCOME_TYPE_CHOICES = [
        ('salary', 'Employment Salary'),
        ('business', 'Business Income'),
        ('rental', 'Rental Income'),
        ('investment', 'Investment Income'),
        ('other', 'Other Income')
    ]

    taxpayer = models.ForeignKey(TaxPayer, on_delete=models.CASCADE, related_name='incomes')
    income_type = models.CharField(max_length=20, choices=INCOME_TYPE_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tax_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    date_received = models.DateField()
    documents = models.FileField(upload_to='income_documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'incomes'
        indexes = [
            models.Index(fields=['taxpayer', 'tax_year']),
            models.Index(fields=['income_type']),
            models.Index(fields=['date_received'])
        ]

class Deduction(models.Model):
    DEDUCTION_TYPE_CHOICES = [
        ('mortgage', 'Mortgage Interest'),
        ('medical', 'Medical Expenses'),
        ('donation', 'Charitable Donations'),
        ('retirement', 'Retirement Contributions'),
        ('education', 'Education Expenses'),
        ('other', 'Other Deductions')
    ]

    taxpayer = models.ForeignKey(TaxPayer, on_delete=models.CASCADE, related_name='deductions')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPE_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tax_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    date_incurred = models.DateField()
    proof_document = models.FileField(upload_to='deduction_documents/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'deductions'
        indexes = [
            models.Index(fields=['taxpayer', 'tax_year']),
            models.Index(fields=['deduction_type']),
            models.Index(fields=['date_incurred'])
        ]

class TaxCalculation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    taxpayer = models.ForeignKey(TaxPayer, on_delete=models.CASCADE, related_name='tax_calculations')
    tax_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    gross_income = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    taxable_income = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    calculation_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'tax_calculations'
        indexes = [
            models.Index(fields=['taxpayer', 'tax_year']),
            models.Index(fields=['status']),
            models.Index(fields=['calculation_date'])
        ]

class TaxRate(models.Model):
    tax_year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    income_from = models.DecimalField(max_digits=12, decimal_places=2)
    income_to = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tax_rates'
        unique_together = ('tax_year', 'income_from', 'income_to')
        indexes = [
            models.Index(fields=['tax_year']),
            models.Index(fields=['income_from', 'income_to'])
        ]