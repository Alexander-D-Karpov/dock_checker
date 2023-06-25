from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.generics import (
    GenericAPIView,
    CreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404,
)
from rest_framework.response import Response

from dock_checker.processor.api.serializers import (
    TaskSerializer,
    FileSerializer,
    FullFileSerializer,
    UpdateFileTitleSerializer,
)
from dock_checker.processor.models import File
from dock_checker.processor.services import get_task_status
from dock_checker.processor.tasks import update_pdf_features


class RetrieveTaskApiView(GenericAPIView):
    serializer_class = TaskSerializer

    def get(self, request, pk):
        data = get_task_status(pk)
        return Response(data=data, status=status.HTTP_200_OK)


class UpdateFileTitleApiView(GenericAPIView):
    serializer_class = UpdateFileTitleSerializer

    def post(self, request, pk):
        file = get_object_or_404(File, pk=pk)
        update_pdf_features.apply_async(
            kwargs={"pk": file.pk, "target": request.data["title"]},
            countdown=1,
        )
        data = FileSerializer().to_representation(file)
        return Response(data=data, status=status.HTTP_200_OK)


class RetrieveFileApiView(RetrieveAPIView):
    queryset = File.objects.all()
    serializer_class = FullFileSerializer


class CreateFileApiView(CreateAPIView):
    parser_classes = [FormParser, MultiPartParser]
    serializer_class = FileSerializer


class ListFileApiView(ListAPIView):
    serializer_class = FileSerializer
    queryset = File.objects.all()
