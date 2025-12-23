import os

if __name__ == '__main__':
    # Django equivalent of Flask's app.run()
    from django.core.management import execute_from_command_line
    
    # Get environment variables
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    port = os.getenv('APP_PORT', '8000')
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    
    # Run Django development server
    execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])