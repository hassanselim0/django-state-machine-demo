from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_state_machine_demo.orders"

    def ready(self):
        # pylint: disable=all
        from . import hooks  # Load all Hooks
