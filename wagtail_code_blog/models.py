# pylint: disable=arguments-differ,too-few-public-methods
# pyright: reportIncompatibleVariableOverride=false

import readtime
from bs4 import BeautifulSoup
from django import forms
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db import models
from markdown import markdown
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images.models import Image
from wagtail.models import Page
from wagtail.search import index
from wagtailmetadata.models import MetadataPageMixin

default_author = "John Doe"


class BlogIndexFieldsMixin(models.Model):
    heading = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    background_color = models.CharField(max_length=250, null=True, blank=True)
    image = models.ForeignKey(
        Image, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        abstract = True


class AuthorNameMixin(models.Model):
    owner = None

    def author_name(self):
        if self.owner and self.owner.first_name and self.owner.last_name:
            return self.owner.first_name + " " + self.owner.last_name
        return default_author

    class Meta:
        abstract = True


BLOG_INDEX_CONTENT_PANELS = [
    FieldPanel("heading"),
    FieldPanel("description"),
    FieldPanel("background_color"),
    FieldPanel("image"),
]


class BlogPageFieldsMixin(models.Model):
    image_url = models.URLField(null=True, blank=True)
    date = models.DateField()
    intro = models.TextField(null=True, blank=True)
    body = models.TextField(default="")
    canonical_url = models.URLField(null=True, blank=True)

    @property
    def readtime(self):
        return readtime.of_markdown(self.body)

    class Meta:
        abstract = True


BLOG_PAGE_SEARCH_FIELDS = [
    index.SearchField("intro"),
    index.SearchField("body"),
]


BLOG_PAGE_INFO_PANELS = [
    FieldPanel("image_url"),
    FieldPanel("canonical_url"),
    FieldPanel("date"),
]


BLOG_PAGE_CONTENT_PANELS = [
    MultiFieldPanel(BLOG_PAGE_INFO_PANELS, heading="Blog information"),
    FieldPanel("intro"),
    FieldPanel("body", widget=forms.Textarea),
]


class AbstractBlogIndexPage(
    MetadataPageMixin, Page, AuthorNameMixin, BlogIndexFieldsMixin
):  # pylint: disable=too-many-ancestors
    paginate_by = 10

    content_panels = Page.content_panels + BLOG_INDEX_CONTENT_PANELS

    class Meta:
        abstract = True

    def get_posts_queryset(self):
        raise NotImplementedError

    def add_paginated_posts_context(self, ctx, posts, request):
        paginator = Paginator(posts, self.paginate_by)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        ctx["posts"] = page_obj.object_list
        ctx["page_obj"] = page_obj
        ctx["paginator"] = paginator
        ctx["is_paginated"] = page_obj.has_other_pages()
        return ctx

    def get_context(self, request):
        ctx = super().get_context(request)
        posts = self.get_posts_queryset()
        return self.add_paginated_posts_context(ctx, posts, request)


class AbstractBlogPage(MetadataPageMixin, Page, AuthorNameMixin, BlogPageFieldsMixin):  # pylint: disable=too-many-ancestors
    search_fields = Page.search_fields + BLOG_PAGE_SEARCH_FIELDS

    content_panels = Page.content_panels + BLOG_PAGE_CONTENT_PANELS

    class Meta:
        abstract = True

    def add_blog_page_context(self, ctx, request):
        site = Site.objects.get_current()
        owner = self.owner
        parent = self.get_parent()
        parent_page = parent.specific if parent else None
        try:
            ctx["author_image"] = owner.wagtail_userprofile.avatar.url  # type: ignore[attr-defined]
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
            body = str(self.body)
            html = markdown(body)
            text = "".join(BeautifulSoup(html, "html.parser").find_all(string=True))
            sd["articleBody"] = text

        try:
            search_image = self.search_image  # type: ignore[attr-defined]
            if search_image:
                rendition = search_image.get_rendition(  # type: ignore[attr-defined]  # pylint: disable=no-member
                    filter="original"
                )
                sd["image"] = [request.build_absolute_uri(rendition.url)]
        except (AttributeError, ObjectDoesNotExist):
            pass

        ctx["blog_background_color"] = getattr(parent_page, "background_color", "")
        ctx["page_sd"] = sd
        return ctx

    def get_context(self, request):
        ctx = super().get_context(request)
        return self.add_blog_page_context(ctx, request)


class BlogIndexPage(AbstractBlogIndexPage):  # pylint: disable=too-many-ancestors
    page_ptr = models.OneToOneField(
        Page, parent_link=True, related_name="+", on_delete=models.CASCADE
    )

    subpage_types = ["wagtail_code_blog.BlogPage"]

    class Meta(Page.Meta):
        pass

    def get_posts_queryset(self):
        return BlogPage.objects.child_of(self).live().order_by("-date")  # type:ignore


class BlogPage(AbstractBlogPage):  # pylint: disable=too-many-ancestors
    page_ptr = models.OneToOneField(
        Page, parent_link=True, related_name="+", on_delete=models.CASCADE
    )
    parent_page_types = ["wagtail_code_blog.BlogIndexPage"]

    class Meta(Page.Meta):
        pass
