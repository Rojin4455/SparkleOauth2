# Generated by Django 5.1.7 on 2025-03-15 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_ghlauthcredentials_token_timestamp_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='access_token',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='company_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='expires_in',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='location_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='refresh_token',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='scope',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='user_id',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='ghlauthcredentials',
            name='user_type',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
