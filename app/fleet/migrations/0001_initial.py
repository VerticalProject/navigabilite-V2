from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('accounts', '0002_user_avatar'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Aircraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration', models.CharField(max_length=20, unique=True, verbose_name='Immatriculation')),
                ('manufacturer', models.CharField(blank=True, max_length=120, verbose_name='Constructeur')),
                ('model', models.CharField(blank=True, max_length=120, verbose_name='Modèle')),
                ('category', models.CharField(choices=[('ULM', 'ULM'), ('SEP', 'Monomoteur piston (SEP)'), ('MEP', 'Multimoteur piston (MEP)')], default='SEP', max_length=8, verbose_name='Catégorie')),
                ('mtow_kg', models.PositiveIntegerField(blank=True, null=True, verbose_name='MTOW (kg)')),
                ('year', models.PositiveIntegerField(blank=True, null=True, verbose_name='Année')),
                ('serial_number', models.CharField(blank=True, max_length=120, verbose_name='N° de série')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aircraft', to='accounts.organization')),
                ('owner_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_aircraft', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['registration']},
        ),
    ]
