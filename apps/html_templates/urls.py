from django.urls import path
from . import views

app_name = 'apps.html_templates'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/html-templates/', views.html_templates_list_create, name='html_templates_create'),
    path('api/html-templates/<uuid:pk>/', views.html_templates_detail, name='html_templates_detail'),
    path('api/html-templates/<uuid:pk>/files/', views.html_templates_upload_files, name='html_templates_upload_files'),
]
