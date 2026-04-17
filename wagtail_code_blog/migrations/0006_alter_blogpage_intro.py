from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtail_code_blog", "0005_blogindexpage_search_image"),
    ]

    operations = [
        migrations.AlterField(
            model_name="blogpage",
            name="intro",
            field=models.TextField(blank=True, null=True),
        ),
    ]
