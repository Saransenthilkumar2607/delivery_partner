#!/usr/bin/env python
"""
Simple script to run Django migrations without loading the full app
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

# Import Django and setup
import django
django.setup()

# Run the migration
from django.core.management import call_command
call_command('migrate', 'app')
