# Generated by Django 4.2.2 on 2023-06-24 14:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("processor", "0004_alter_fileimage_unique_together_fileimage_file_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="file",
            name="preview",
        ),
    ]