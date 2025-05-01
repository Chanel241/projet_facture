from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Base URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
]

# Internationalized URL patterns
urlpatterns += i18n_patterns(
    path('', include('facture_app.urls')),
)

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'facture_app.views.custom_404'
handler500 = 'facture_app.views.custom_500'