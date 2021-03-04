# pylint: disable=arguments-differ,too-few-public-methods
import readtime
from bs4 import BeautifulSoup
from django import forms
from django.contrib.sites.models import Site
from django.db import models
from markdown import markdown
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel
from wagtail.core.models import Page
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import Image
from wagtail.search import index
from wagtail.users.models import UserProfile
from wagtailmetadata.models import MetadataPageMixin

default_author = "John Doe"


class AuthorNameMixin(models.Model):
    owner = None  # type: UserProfile

    def author_name(self):
        if self.owner and self.owner.first_name and self.owner.last_name:
            return self.owner.first_name + " " + self.owner.last_name
        return default_author

    class Meta:
        abstract = True
        auto_created = True


class BlogIndexPage(MetadataPageMixin, Page, AuthorNameMixin):
    page_ptr = models.OneToOneField(
        Page, parent_link=True, related_name="+", on_delete=models.CASCADE
    )

    heading = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    background_color = models.CharField(max_length=250, null=True, blank=True)
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    subpage_types = ["wagtail_code_blog.BlogPage"]

    content_panels = Page.content_panels + [
        FieldPanel("heading"),
        FieldPanel("description"),
        FieldPanel("background_color"),
        ImageChooserPanel("image"),
    ]

    def get_context(self, request):
        ctx = super().get_context(request)
        ctx["posts"] = (
            BlogPage.objects.child_of(self).live().order_by("-date")  # type:ignore
        )
        return ctx


class BlogPage(MetadataPageMixin, Page, AuthorNameMixin):
    page_ptr = models.OneToOneField(
        Page, parent_link=True, related_name="+", on_delete=models.CASCADE
    )
    parent_page_types = ["wagtail_code_blog.BlogIndexPage"]

    image_url = models.URLField(null=True, blank=True)
    date = models.DateField()
    intro = models.CharField(max_length=250, null=True, blank=True)
    body = models.TextField(default="")
    canonical_url = models.URLField(null=True, blank=True)

    @property
    def readtime(self):
        return readtime.of_markdown(self.body)

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("image_url"), FieldPanel("canonical_url"), FieldPanel("date")],
            heading="Blog information",
        ),
        FieldPanel("intro"),
        FieldPanel("body", widget=forms.Textarea),
    ]

    def get_context(self, request):
        ctx = super().get_context(request)
        site = Site.objects.get_current()
        try:
            ctx["author_image"] = self.owner.wagtail_userprofile.avatar.url
        except AttributeError:
            pass
        except Exception as ex:  # pylint: disable=broad-except
            if ex.args != ("User has no wagtail_userprofile.",):
                raise ex

        sd = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "mainEntity": {
                "@type": "WebPage",
                "@id": site.domain,
            },
            "headline": self.title,
            "datePublished": self.date,
        }

        if site.name:
            sd["publisher"] = (
                {
                    "@type": "Organization",
                    "name": site.name,
                },
            )

        if self.author_name() is not default_author:
            sd["author"] = (
                {
                    "@type": "Person",
                    "name": self.author_name(),
                },
            )

        if self.body:
            html = markdown(self.body)
            text = "".join(BeautifulSoup(html, "html.parser").findAll(text=True))
            sd["articleBody"] = text

        if self.search_image:
            rendition = self.search_image.get_rendition(  # pylint: disable=no-member
                filter="original"
            )
            sd["image"] = [request.build_absolute_uri(rendition.url)]

        ctx["page_sd"] = sd

        return ctx
