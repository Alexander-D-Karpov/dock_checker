# Generated by Django 4.2.2 on 2023-06-24 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("processor", "0006_fileimage_text_alter_file_file"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Task",
        ),
        migrations.RemoveField(
            model_name="fileimage",
            name="text",
        ),
        migrations.AddField(
            model_name="file",
            name="ideal_title",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="file",
            name="text_locations",
            field=models.JSONField(default=dict),
        ),
    ]