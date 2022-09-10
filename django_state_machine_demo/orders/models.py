from __future__ import annotations

from django.db import models
from model_utils.fields import AutoCreatedField, MonitorField

from ..utils.enums import ChoicesEnum, EnumField, HooksMixin


class Order(models.Model):
    class State(HooksMixin, ChoicesEnum):
        PENDING_PAYMENT = "pending_payment"
        PROCESSING = "processing"
        OUT_FOR_DELIVERY = "out_for_delivery"
        DELIVERED = "delivered", "Package Delivered"
        CANCELLED = "cancelled"
        REFUNDED = "refunded"

    item = models.CharField("Item", max_length=100)
    state = EnumField("State", State, default=State.PENDING_PAYMENT)
    state_changed = MonitorField("State Changed", monitor="state")
    price = models.DecimalField("Price", max_digits=8, decimal_places=2)
    metadata = models.JSONField("Metadata", default=dict, blank=True)

    objects: models.Manager[Order]
    logs: models.manager.RelatedManager[OrderLog]

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        db_table = "orders"

    _state_map = {
        State.PENDING_PAYMENT: (State.PROCESSING, State.CANCELLED),
        State.PROCESSING: (State.OUT_FOR_DELIVERY, State.REFUNDED),
        State.OUT_FOR_DELIVERY: (State.DELIVERED, State.REFUNDED),
        State.DELIVERED: (State.REFUNDED,),
    }

    def get_possible_next_states(self) -> tuple[State]:
        return self._state_map.get(self.state, ())

    def transition_state(self, new_state: State, **kwargs):
        old_state = self.state

        if new_state not in self.get_possible_next_states():
            raise ValueError(f"Can't transition from {old_state} to {new_state}")

        new_state.execute_hooks("before", self, **kwargs)

        self.state = new_state
        self.save()

        self.logs.create(old_state=old_state, new_state=new_state, extra=kwargs)

        new_state.execute_hooks("after", self, **kwargs)


class OrderLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="logs")
    timestamp = AutoCreatedField("Timestamp")
    old_state = EnumField("Old State", Order.State)
    new_state = EnumField("New State", Order.State)
    extra = models.JSONField("Extra", default=dict, blank=True)

    order_id: int
    objects: models.Manager[OrderLog]

    class Meta:
        verbose_name = "Order Log"
        verbose_name_plural = "Order Logs"
        db_table = "order_logs"

    def __str__(self) -> str:
        return (
            f'Order #{self.order_id}: {self.old_state or "(blank)"} -> {self.new_state} '
            f"@ {self.timestamp:%Y-%m-%d %H:%M:%S}"
        )
