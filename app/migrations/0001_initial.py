"""
Create users table equivalent to SQLAlchemy User model
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID'
                    )
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),

                # Common fields
                ('email', models.EmailField(
                    unique=True,
                    db_index=True,
                    max_length=254
                )),
                ('name', models.CharField(max_length=100)),
                ('password_hash', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),

                ('role', models.CharField(
                    max_length=20,
                    choices=[
                        ('END_USER', 'END_USER'),
                        ('DELIVERY_PARTNER', 'DELIVERY_PARTNER'),
                        ('ADMIN', 'ADMIN'),
                    ],
                    default='END_USER'
                )),

                ('phone_number', models.CharField(
                    max_length=20,
                    null=True,
                    blank=True
                )),

                # Address fields (End User)
                ('address_line_1', models.CharField(
                    max_length=255,
                    null=True,
                    blank=True
                )),
                ('address_line_2', models.CharField(
                    max_length=255,
                    null=True,
                    blank=True
                )),
                ('city', models.CharField(
                    max_length=100,
                    null=True,
                    blank=True
                )),
                ('state', models.CharField(
                    max_length=100,
                    null=True,
                    blank=True
                )),
                ('postal_code', models.CharField(
                    max_length=20,
                    null=True,
                    blank=True
                )),
                ('country', models.CharField(
                    max_length=100,
                    default='india'
                )),
                ('delivery_notes', models.TextField(
                    null=True,
                    blank=True
                )),

                # Delivery Partner fields
                ('license_number', models.CharField(
                    max_length=50,
                    null=True,
                    blank=True
                )),
                ('vehicle_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('BIKE', 'BIKE'),
                        ('CAR', 'CAR'),
                        ('VAN', 'VAN'),
                        ('TRUCK', 'TRUCK'),
                    ],
                    null=True,
                    blank=True
                )),
                ('vehicle_number', models.CharField(
                    max_length=20,
                    null=True,
                    blank=True
                )),
                ('is_verified', models.BooleanField(default=False)),
                ('rating', models.FloatField(default=0.0)),
                ('total_deliveries', models.IntegerField(default=0)),

                # Admin fields
                ('department', models.CharField(
                    max_length=100,
                    null=True,
                    blank=True
                )),

                # Documents (S3 paths)
                ('license_document', models.CharField(
                    max_length=500,
                    null=True,
                    blank=True
                )),
                ('vehicle_document', models.CharField(
                    max_length=500,
                    null=True,
                    blank=True
                )),
                ('profile_photo', models.CharField(
                    max_length=500,
                    null=True,
                    blank=True
                )),
            ],
            options={
                'db_table': 'users',
                'ordering': ['-created_at'],
            },
        ),
    ]
