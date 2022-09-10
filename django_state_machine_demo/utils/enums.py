from __future__ import annotations

import logging
import math
from enum import Enum, EnumMeta

from django.db import models


class ChoicesEnumMeta(EnumMeta):
    @staticmethod
    def _get_mixins_(class_name, bases):
        # This trick makes it possible to define enum members with tuple syntax
        # no matter what the bases are for ChoicesEnum
        _, first_enum = EnumMeta._get_mixins_(class_name, bases)
        return tuple, first_enum

    def __contains__(cls: ChoicesEnum, member):
        return member in cls._member_map_.values()


class ChoicesEnum(str, Enum, metaclass=ChoicesEnumMeta):
    """
    An Enum Base Class that can generate Django ORM Field Choices
    Enum Values should be either a string or a tuple of size 2,
    if the value was a string, the choice description is auto-generated.
    ```
    class Example(ChoicesEnum):
        ACTIVE = 'active'
        DISABLED = ('disabled', 'Item Disabled')

    state = models.CharField(choices=Example.choices())
    ```
    """

    # pylint: disable=no-member

    def __new__(cls, value):
        obj = str.__new__(cls, value[0])
        obj._value_ = value[0]
        return obj

    def __init__(self, value):
        self.desc = value[1] if len(value) > 1 else self._name_.replace("_", " ").title()
        super().__init__()

    @classmethod
    def choices(cls):
        return [(e.value, e.desc) for e in cls]

    @classmethod
    def is_valid(cls, value):
        if isinstance(value, cls):
            return True
        if isinstance(value, str):
            return value in (e.value for e in cls)
        return False


class EnumField(models.CharField):
    """
    A Django Model Field Class that makes using ChoicesEnum a lot better.
    The `choices` are provided, and `max_length` is smartly calculated.
    All that decreases the amount of migration creation/modification.
    It also makes sure the value you read from the model field has the proper enum type.
    Now your enum and model can look like this:
    ```
    class Example(ChoicesEnum):
        ACTIVE = 'active'
        DISABLED = 'disabled'
        _DEFAULT = ACTIVE

    state = EnumField('State', Example)
    ```
    """

    _logger = logging.getLogger(f"{__name__}.EnumField")

    def __init__(self, verbose_name, enum_cls, *args, **kwargs):
        assert issubclass(enum_cls, ChoicesEnum), "EnumField only works with ChoicesEnum"

        self.enum_cls = enum_cls

        if hasattr(enum_cls, "_DEFAULT"):
            kwargs.setdefault("default", enum_cls._DEFAULT)

        # A safe guess for max_length: Smallest power-of-two that allows all values
        if "max_length" not in kwargs:
            max_length = max(len(e.value) for e in enum_cls)
            max_length = int(math.pow(2, math.ceil(math.log2(max_length))))
            kwargs["max_length"] = max(max_length, 16)

        kwargs["choices"] = enum_cls.choices()

        super().__init__(verbose_name, *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_cls"] = self.enum_cls
        kwargs.pop("choices", None)
        if "default" in kwargs:
            kwargs["default"] = str(kwargs["default"])
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        if value == "" and self.blank:
            return ""
        if not isinstance(value, (str, ChoicesEnum)):
            raise TypeError("Field Value Type should be str or ChoicesEnum")
        if not self.enum_cls.is_valid(value):
            self._logger.warning(
                "Unexpected %s Value: %s", self.enum_cls.__name__, value, exc_info=True
            )
        return str(value)

    def from_db_value(self, value, *args, **kwargs):
        # pylint: disable=unused-argument
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return None
        if value == "" and self.blank:
            return ""
        if not self.enum_cls.is_valid(value):
            self._logger.warning(
                "Unexpected %s Value: %s", self.enum_cls.__name__, value, exc_info=True
            )
            return value
        return self.enum_cls(value)


class HooksMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hooks = {}

    def register_hook(self, name):
        if name not in self._hooks:
            self._hooks[name] = []

        def decorator(func):
            self._hooks[name].append(func)
            return func

        return decorator

    def execute_hooks(self, name, *args, **kwargs):
        if name not in self._hooks:
            return

        for hook in self._hooks[name]:
            hook(*args, **kwargs)
