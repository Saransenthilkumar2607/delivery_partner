"""
Add Delivery model with foreign key relationships
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Delivery',
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

                # Basic Information
                ('tracking_number', models.CharField(
                    max_length=50,
                    unique=True,
                    db_index=True
                )),

                # Delivery Details
                ('pickup_address', models.TextField()),
                ('delivery_address', models.TextField()),
                ('item_description', models.TextField()),

                # Status and Tracking
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('PENDING', 'PENDING'),
                        ('ASSIGNED', 'ASSIGNED'),
                        ('PICKED_UP', 'PICKED_UP'),
                        ('DELIVERED', 'DELIVERED'),
                        ('CANCELLED', 'CANCELLED'),
                    ],
                    default='PENDING'
                )),

                # Timing
                ('pickup_time', models.DateTimeField(null=True, blank=True)),
                ('delivery_time', models.DateTimeField(null=True, blank=True)),

                # Pricing
                ('delivery_fee', models.DecimalField(
                    max_digits=10,
                    decimal_places=2,
                    null=True,
                    blank=True
                )),
                ('tip', models.DecimalField(
                    max_digits=10,
                    decimal_places=2,
                    default=0
                )),

                # Notes
                ('pickup_notes', models.TextField(null=True, blank=True)),
                ('delivery_notes', models.TextField(null=True, blank=True)),

                # Foreign Keys
                ('end_user', models.ForeignKey(
                    to='app.user',
                    related_name='user_deliveries',
                    on_delete=django.db.models.deletion.CASCADE
                )),
                ('delivery_partner', models.ForeignKey(
                    to='app.user',
                    related_name='partner_deliveries',
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True
                )),
            ],
            options={
                'db_table': 'deliveries',
                'ordering': ['-created_at'],
            },
        ),
    ]
