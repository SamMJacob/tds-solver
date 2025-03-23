import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tds_solver.settings")  # Update with your settings module
app = get_wsgi_application()
