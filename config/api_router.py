from django.urls import path, include

app_name = "api"
urlpatterns = [path("", include("dock_checker.processor.api.urls"))]
