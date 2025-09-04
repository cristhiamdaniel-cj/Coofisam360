from django.urls import path
from . import api_views

urlpatterns = [
    path('status/', api_views.api_status, name='api-status'),
    path('test/', api_views.api_test_data, name='api-test'),
    path('users/', api_views.UserListView.as_view(), name='api-user-list'),
    path('users/<int:pk>/', api_views.UserDetailView.as_view(), name='api-user-detail'),
    path('profile/', api_views.user_profile, name='api-user-profile'),
]
