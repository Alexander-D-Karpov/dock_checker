from django.urls import path

from dock_checker.processor.api.views import (
    CreateFileApiView,
    RetrieveTaskApiView,
    ListFileApiView,
    RetrieveFileApiView,
    UpdateFileTitleApiView,
)

urlpatterns = [
    path("list", ListFileApiView.as_view()),
    path("upload/", CreateFileApiView.as_view()),
    path("status/<str:pk>", RetrieveTaskApiView.as_view(), name="status"),
    path("file/<str:pk>", RetrieveFileApiView.as_view(), name="file"),
    path("file/<str:pk>/update/", UpdateFileTitleApiView.as_view()),
]
