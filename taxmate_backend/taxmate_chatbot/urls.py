from django.urls import path, include # type: ignore
from rest_framework.routers import DefaultRouter # type: ignore
from .views import ChatbotView

# Create router and register viewset
router = DefaultRouter()
router.register(r'chatbot', ChatbotView, basename='chatbot')

# Wire up our API using automatic URL routing
urlpatterns = [
    path('', include(router.urls)),
]