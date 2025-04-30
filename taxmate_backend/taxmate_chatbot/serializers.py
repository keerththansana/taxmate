from rest_framework import serializers # type: ignore
from .models import (
    TaxSlab, IncomeType, Deduction, QualifyingPayment,
    TaxCalendar, FAQStatic
)

class TaxSlabSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxSlab
        fields = '__all__'

class DeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = '__all__'

class FAQStaticSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQStatic
        fields = '__all__'