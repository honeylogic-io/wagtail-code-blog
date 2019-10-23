import pytest
from bs4 import BeautifulSoup
from django.utils import timezone
from wagtail.core.models import Site

from wagtail_code_blog.models import BlogIndexPage, BlogPage


@pytest.mark.django_db
def test_canonical_url(client):
    site = Site.objects.first()
    index = BlogIndexPage(title="blog")
    site.root_page.add_child(instance=index)
    post = BlogPage(
        title="My post", canonical_url="https://foo.com", date=timezone.now()
    )
    index.add_child(instance=post)

    res = client.get(post.get_url())
    soup = BeautifulSoup(res.content, "html.parser")
    el = soup.find("link", attrs={"rel": "canonical"})
    assert el["href"] == "https://foo.com"
