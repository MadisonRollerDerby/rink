from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import reverse
from django.views.generic import TemplateView, RedirectView
from django.views import defaults as default_views

urlpatterns = [
    #url(r'^$', TemplateView.as_view(template_name='pages/home.html'), name='home'),
    url(r'^$', RedirectView.as_view(url='/billing/pay', permanent=False), name="home"),
    url(r'^about$', TemplateView.as_view(template_name='pages/about.html'), name='about'),

    # Django Admin, use {% url 'admin:index' %}
    url(settings.ADMIN_URL, admin.site.urls),

    # User management
    url(r'^users/', include('rink.users.urls', namespace='users')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^billing/', include('billing.urls', namespace='billing')),
    url(r'^legal/', include('legal.urls', namespace='legal')),
    url(r'^organization/', include('league.urls', namespace='league')),
    url(r'^register/', include('registration.urls', namespace="register")),
    url(r'^registration/', include('registration.urls_admin', namespace='registration')),
    url(r'^roster/', include('roster.urls', namespace='roster')),
    url(r'^tickets/', include('tickets.urls', namespace='tickets')),
    url(r'^voting/', include('voting.urls', namespace='voting')),

    url(r'^robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name="robots_file")




] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        url(r'^403/$', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        url(r'^404/$', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        url(r'^500/$', default_views.server_error),
    ]

if 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
