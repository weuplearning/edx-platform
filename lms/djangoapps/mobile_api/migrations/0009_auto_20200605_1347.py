# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-06-05 13:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobile_api', '0008_auto_20200228_1051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appversionconfig',
            name='platform',
            field=models.CharField(choices=[('Android', 'Android'), ('iOS', 'iOS')], max_length=50),
        ),
    ]
