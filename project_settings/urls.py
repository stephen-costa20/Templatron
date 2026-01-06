from django.urls import path, include
from apps.html_templates import views as html_template_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', html_template_views.home, name='home_root'), 
    path('html-templates/', include('apps.html_templates.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)