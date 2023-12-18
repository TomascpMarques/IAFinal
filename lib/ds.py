from __future__ import annotations
from typing import Generic
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')


class SimpleQueue(Generic[T]):
    __content: list[T]

    def __init__(self, *args: T) -> None:
        self.__content = list(args)

    def push(self, item: T) -> None:
        self.__content.append(item)

    def pop(self) -> T | None:
        if len(self.__content) < 1:
            return None
        return_value = self.__content[0]
        self.__content = self.__content[1:]
        return return_value

    def peek(self) -> T | None:
        if len(self.__content) < 1:
            return None
        return self.__content[0]

    def has_next(self) -> bool:
        return len(self.__content) != 0

    def elements(self) -> list[T]:
        return self.__content.copy()
