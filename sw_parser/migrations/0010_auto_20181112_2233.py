# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-13 06:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sw_parser', '0009_auto_20181107_2220'),
    ]

    operations = [
        migrations.AlterField(
            model_name='magicboxcraft',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='riftdungeonlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='riftraidlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='runecraftlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='runlog',
            name='level',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='bestiary.Level'),
        ),
        migrations.AlterField(
            model_name='runlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='shoprefreshlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='summonlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='wishlog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
        migrations.AlterField(
            model_name='worldbosslog',
            name='summoner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='herders.Summoner'),
        ),
    ]
