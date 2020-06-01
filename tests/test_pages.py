import json

import pytest
from bs4 import BeautifulSoup
from django.utils import timezone
from foliage.contextmanagers import page_tree

from wagtail_code_blog.models import BlogIndexPage, BlogPage  # isort:skip

pytestmark = pytest.mark.django_db


def test_blog_index(client):
    pages = [
        (
            BlogIndexPage(title="index"),
            [BlogPage(title="My post", body="some text", date=timezone.now())],
        )
    ]
    with page_tree(pages):
        [(index, [post])] = pages
        res = client.get(index.get_url())
        assert res.status_code == 200
        assert list(res.context["posts"]) == [post]


def test_blog_page(client):
    pages = [
        (
            BlogIndexPage(title="index"),
            [BlogPage(title="My post", date=timezone.now(), body="some text",)],
        )
    ]
    with page_tree(pages):
        [(_, [post])] = pages
        res = client.get(post.get_url())
        assert res.status_code == 200
        assert post.readtime.text == "1 min"

        soup = BeautifulSoup(res.content, "html.parser")
        ld_json = json.loads(soup.find("script").string)
        assert ld_json["articleBody"] == "some text"
        assert ld_json["headline"] == "My post"
        assert ld_json["mainEntity"] == {"@id": "localhost", "@type": "WebPage"}


def test_canonical_url(client):
    post = BlogPage(
        title="My post",
        canonical_url="https://foo.com",
        body="some text",
        date=timezone.now(),
    )
    pages = [(BlogIndexPage(title="index"), [post])]
    with page_tree(pages):
        [(_, [post])] = pages
        res = client.get(post.get_url())
        assert res.status_code == 200
        soup = BeautifulSoup(res.content, "html.parser")
        el = soup.find("link", attrs={"rel": "canonical"})
        assert el["href"] == "https://foo.com"


def test_renders_toc(client):
    post = BlogPage(
        title="My post",
        body="""
[TOC]
# first paragraph""",
        date=timezone.now(),
    )
    pages = [(BlogIndexPage(title="index"), [post])]
    with page_tree(pages):
        [(_, [post])] = pages
        res = client.get(post.get_url())
    assert res.status_code == 200
    assert BeautifulSoup(res.content, "html.parser").select(".toc")
