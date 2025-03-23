from django.urls import path
from .views import TDSSolverView

urlpatterns = [
    path('', TDSSolverView.as_view(), name='tds_solver'),
]