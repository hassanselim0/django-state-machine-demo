import locale
from datetime import datetime

from .models import Order


@Order.State.PROCESSING.register_hook("before")
def validate_payment_method(order: Order, payment_method=None, **kwargs):
    if payment_method not in ("cash", "card"):
        raise ValueError(f"Invalid payment method: {payment_method}")
    order.metadata["payment_method"] = payment_method


@Order.State.PROCESSING.register_hook("before")
def apply_discount(order: Order, discount=None, **kwargs):
    if discount is None:
        return

    if not 0 <= discount <= 100:
        raise ValueError(f"Invalid discount percentage: {discount}")

    order.price = order.price * (1 - discount / 100)
    order.metadata["discount"] = discount


@Order.State.PROCESSING.register_hook("after")
def notify_payment_success(order: Order, payment_method, **kwargs):
    print(f"\u001b[32mPayment for order #{order.id} successful!")
    print(f"\u001b[32mTotal: {order.price} (paid with {payment_method})")


@Order.State.OUT_FOR_DELIVERY.register_hook("before")
def validate_delivery_date(order: Order, delivery_date=None, **kwargs):
    if delivery_date is None:
        raise ValueError("Delivery date is required")

    parsed_date = datetime.fromisoformat(delivery_date)
    if parsed_date < datetime.now():
        raise ValueError("Delivery date must be in the future")

    order.metadata["delivery_date"] = delivery_date


@Order.State.OUT_FOR_DELIVERY.register_hook("after")
def notify_out_for_delivery(order: Order, delivery_date, **kwargs):
    locale.setlocale(locale.LC_ALL, "")
    parsed_date = datetime.fromisoformat(delivery_date)
    print(f"\u001b[32mOrder #{order.id} is out for delivery!")
    print(f"\u001b[32mDelivery date: {parsed_date:%c}")


@Order.State.DELIVERED.register_hook("after")
def notify_delivery_success(order: Order, **kwargs):
    print(f"\u001b[32mOrder #{order.id} delivered successfully!")


@Order.State.CANCELLED.register_hook("after")
@Order.State.REFUNDED.register_hook("after")
def send_questionnaire(order: Order, **kwargs):
    print("\u001b[32mWe're sad to see you go! Please fill out this questionnaire:")
    qr_code = """
        ┌─────────────────────────────────────┐
        │                                     │
        │    ▄▄▄▄▄▄▄ ▄▄    ▄ ▄▄▄▄▄ ▄▄▄▄▄▄▄    │
        │    █ ▄▄▄ █ ▄  ▄▄█▄  ▀█ ▄ █ ▄▄▄ █    │
        │    █ ███ █ ██▄█ █ █▀▀▀█  █ ███ █    │
        │    █▄▄▄▄▄█ ▄▀▄ █▀▄ ▄▀█▀█ █▄▄▄▄▄█    │
        │    ▄▄▄▄  ▄ ▄▀ ▀ ▄▄▀▀███▀▄  ▄▄▄ ▄    │
        │    ▄▄█▄█▀▄▀▄▀   ▄▀ █ ▄▀█ ███ ▄▄▀    │
        │     █▄█▀▄▄▀ ▄ █▀██▄█▄▀▄▀▀▀▀▀▄▄ ▀    │
        │    █▀▄▀██▄ ▀▄█▀▄ █ █▀ ██▄▀█▄ ███    │
        │    █▀▄██ ▄ ▀ ▄▄▀ ▀▀▀ ▄ █▄▀▀█▄ █     │
        │    ▄▀▀▄▀ ▄▀██▄▄█ ▀█▄ ▀ ▀▀ █ ▀█▀     │
        │     ▄▀█▀▀▄▄▄▄▄▄█ █▄▀█▄███▄▄▄▄█      │
        │    ▄▄▄▄▄▄▄ ▀██▄█▄▄   ▀▄█ ▄ ██▀█▀    │
        │    █ ▄▄▄ █  ▀▄ ▄▀██▄▄▀ █▄▄▄█▀▄█▄    │
        │    █ ███ █ █ ▄█▀▄ ▀▀  ▀▀█ ▄▀▀▄ █    │
        │    █▄▄▄▄▄█ █  ▀  █▄█ ▀██  ▀ █ █     │
        │                                     │
        └─────────────────────────────────────┘
    """
    print("\r\n".join(f"\u001b[30m\u001b[47m{l.strip()}\u001b[0m" for l in qr_code.splitlines()))
