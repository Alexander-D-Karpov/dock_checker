from django.apps import AppConfig


class ProcessorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dock_checker.processor"

    def ready(self):
        import dock_checker.processor.signals
