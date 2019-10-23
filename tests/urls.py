from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import Sitemap as wagtail_sitemap
from wagtail.core import urls as wagtail_urls
from wagtail.images import urls

urlpatterns = [
    path("cms/", include(wagtailadmin_urls)),
    path("", include(wagtail_urls)),
]
