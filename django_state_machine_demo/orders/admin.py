import json
from django.contrib import admin
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from .models import Order, OrderLog


class OrderAdmin(admin.ModelAdmin):
    list_display = ("item", "state", "state_changed", "price", "metadata")
    readonly_fields = ("state", "state_changed", "operations")

    def get_inlines(self, request, obj):
        return (OrderLogInline,)

    def operations(self, obj: Order):
        return mark_safe(
            'Extra Data:<br /><textarea name="__extra">{}</textarea><br />'
        ) + format_html_join(
            " ",
            '<button class="button" type="submit" value="{0}" name="__transition_state">{1}</button>',
            ((s, s.desc) for s in obj.get_possible_next_states()),
        )

    def response_change(self, request, obj: Order):
        new_state = request.POST.get("__transition_state")
        extra = request.POST.get("__extra")
        if new_state:
            try:
                obj.transition_state(Order.State(new_state), **json.loads(extra))
            except ValueError as err:
                self.message_user(request, str(err), level="error")
            request.POST = request.POST.copy()
            request.POST["_continue"] = ""

        return super().response_change(request, obj)


class OrderLogInline(admin.TabularInline):
    model = OrderLog
    readonly_fields = ("timestamp", "old_state", "new_state", "extra")
    add = False
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj):
        return False


admin.site.register(Order, OrderAdmin)
