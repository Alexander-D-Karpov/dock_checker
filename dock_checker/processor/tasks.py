import os

import shutil
from time import sleep

from celery import shared_task
from django.core.files import File
from pdf2image import convert_from_path
from django.core.cache import cache
from pypdf import PdfReader

from dock_checker.processor.models import File as FileModel, FileImage
from ml.main import (
    extract_test_features,
    inference_models,
    create_test_features,
    get_matches,
)


@shared_task
def process_pdf(pk: str):
    file = FileModel.objects.get(pk=pk)
    reader = PdfReader(file.file.path)
    cache.set(f"{pk}-total", len(reader.pages))
    cache.set(f"{pk}-features_loaded", False)
    cache.set(f"{pk}-processed", 1)
    extract_pdf_features.apply_async(kwargs={"pk": pk})
    split_pdf_into_images.apply_async(kwargs={"pk": pk})
    load_pdf.apply_async(kwargs={"pk": pk})
    return pk


@shared_task
def extract_pdf_features(pk: str):
    file = FileModel.objects.get(pk=pk)
    data, status = extract_test_features(file.file.path)
    if not status:
        print(data)
        cache.set(f"{pk}-error", True)
        cache.set(f"{pk}-error_description", data)
    else:
        # TODO: create new file for download
        data = create_test_features(data)
        _, target = inference_models("ml/checkpoints/models.pkl", data)
        text_locations = get_matches(file.file.path, target)
        file.ideal_title = target
        file.text_locations = text_locations
        file.save()
    cache.set(f"{pk}-features_loaded", True)
    return pk


@shared_task
def update_pdf_features(pk: str, target: str):
    file = FileModel.objects.get(pk=pk)
    cache.set(f"{pk}-features_loaded", False)
    data, status = extract_test_features(file.file.path)
    if not status:
        print(data)
        cache.set(f"{pk}-error", True)
        cache.set(f"{pk}-error_description", data)
    else:
        # TODO: create new file for download
        text_locations = get_matches(file.file.path, target)
        file.ideal_title = target
        file.text_locations = text_locations
        file.save()
    cache.set(f"{pk}-features_loaded", True)
    return pk


@shared_task
def split_pdf_into_images(pk: str):
    file = FileModel.objects.get(pk=pk)
    os.mkdir(str(pk))
    convert_from_path(file.file.path, output_folder=str(pk), paths_only=True, fmt="png")
    return pk


def get_file(pk: str, number: int):
    res = {}
    for e in os.listdir(str(pk)):
        p = int(e.split("-")[-1].split(".")[0])
        res[p] = e

    if number == len(os.listdir(str(pk))):
        sleep(1)
        return res[number]
    if number + 1 in res:
        return res[number]

    return False


@shared_task
def load_pdf(pk: str):
    file = FileModel.objects.get(pk=pk)
    if not os.path.isdir(str(pk)):
        load_pdf.apply_async(
            kwargs={"pk": pk},
            countdown=1,
        )
        return

    for i in range(cache.get(f"{pk}-processed"), cache.get(f"{pk}-total") + 1):
        cache.set(f"{pk}-processed", i)
        f_path = get_file(pk, i)
        if f_path:
            with open(str(pk) + "/" + f_path, "rb") as f:
                FileImage.objects.create(
                    image=File(f, name=f"{pk}-{i}.png"), file=file, order=i
                )
                print(i)
        else:
            load_pdf.apply_async(
                kwargs={"pk": pk},
                countdown=1,
            )
            return
    shutil.rmtree(str(pk))
    return pk
