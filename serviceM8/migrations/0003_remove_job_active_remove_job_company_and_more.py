# Generated by Django 5.1.7 on 2025-03-15 18:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('serviceM8', '0002_client_job'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='job',
            name='active',
        ),
        migrations.RemoveField(
            model_name='job',
            name='company',
        ),
        migrations.RemoveField(
            model_name='job',
            name='created_by_staff_uuid',
        ),
        migrations.RemoveField(
            model_name='job',
            name='date',
        ),
        migrations.AddField(
            model_name='job',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job', to='serviceM8.client'),
        ),
        migrations.AddField(
            model_name='job',
            name='job_address',
            field=models.TextField(blank=True, null=True),
        ),
    ]
