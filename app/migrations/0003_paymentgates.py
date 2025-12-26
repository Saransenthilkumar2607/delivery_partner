"""
Add Payment and PaymentRefund models for Razorpay integration
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_delivery'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
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
                ('order_id', models.CharField(
                    max_length=100,
                    unique=True,
                    db_index=True
                )),
                ('razorpay_order_id', models.CharField(
                    max_length=100,
                    unique=True,
                    db_index=True
                )),
                ('razorpay_payment_id', models.CharField(
                    max_length=100,
                    unique=True,
                    db_index=True,
                    null=True,
                    blank=True
                )),
                ('razorpay_signature', models.CharField(
                    max_length=500,
                    null=True,
                    blank=True
                )),

                # Payment Details
                ('amount', models.FloatField()),
                ('currency', models.CharField(
                    max_length=3,
                    default='INR'
                )),
                ('method', models.CharField(
                    max_length=20,
                    default='RAZORPAY'
                )),
                ('status', models.CharField(
                    max_length=20,
                    default='PENDING'
                )),

                # Payment Metadata
                ('notes', models.JSONField(
                    null=True,
                    blank=True
                )),
                ('error_description', models.TextField(
                    null=True,
                    blank=True
                )),

                # Timestamps
                ('payment_completed_at', models.DateTimeField(
                    null=True,
                    blank=True
                )),
                ('refund_initiated_at', models.DateTimeField(
                    null=True,
                    blank=True
                )),
                ('refund_completed_at', models.DateTimeField(
                    null=True,
                    blank=True
                )),

                # Foreign Keys
                ('user', models.ForeignKey(
                    to='app.user',
                    on_delete=django.db.models.deletion.CASCADE
                )),
                ('delivery', models.ForeignKey(
                    to='app.delivery',
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True
                )),
            ],
            options={
                'db_table': 'payments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentRefund',
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
                ('refund_id', models.CharField(
                    max_length=100,
                    unique=True,
                    db_index=True
                )),
                ('razorpay_refund_id', models.CharField(
                    max_length=100,
                    unique=True,
                    db_index=True,
                    null=True,
                    blank=True
                )),

                # Refund Details
                ('amount', models.FloatField()),
                ('reason', models.CharField(
                    max_length=255,
                    null=True,
                    blank=True
                )),
                ('status', models.CharField(
                    max_length=20,
                    default='PENDING'
                )),

                # Processing Information
                ('processed_by', models.CharField(
                    max_length=100,
                    null=True,
                    blank=True
                )),
                ('notes', models.TextField(
                    null=True,
                    blank=True
                )),

                # Timestamps
                ('refund_initiated_at', models.DateTimeField()),
                ('refund_completed_at', models.DateTimeField(
                    null=True,
                    blank=True
                )),

                # Foreign Keys
                ('payment', models.ForeignKey(
                    to='app.payment',
                    on_delete=django.db.models.deletion.CASCADE
                )),
            ],
            options={
                'db_table': 'payment_refunds',
                'ordering': ['-created_at'],
            },
        ),
    ]
