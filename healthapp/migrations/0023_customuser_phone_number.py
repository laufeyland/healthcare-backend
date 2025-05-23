# Generated by Django 5.1.6 on 2025-04-18 02:39

from django.db import migrations, models
from ..models import CustomUser  # Adjust the import based on your project structure

def set_incremental_phone_number(apps, schema_editor):
        CustomUser = apps.get_model('healthapp', 'CustomUser')
        users = CustomUser.objects.all()
    
        # Incremental value starting at 1
        for i, user in enumerate(users, start=1):
            user.phone_number = str(i)  # Set phone number as a string, e.g., '1', '2', etc.
            user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('healthapp', '0022_remove_customuser_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(max_length=20, unique=True, null=True),
            preserve_default=False,
        ),
        migrations.RunPython(set_incremental_phone_number),
    ]
