from django.apps import AppConfig


class WagtailBlogConfig(AppConfig):
    name = "wagtail_code_blog"

    def ready(self):
        try:
            # pylint: disable=unused-import,import-outside-toplevel
            import wagtail_code_blog.signals
        except ImportError:
            pass
