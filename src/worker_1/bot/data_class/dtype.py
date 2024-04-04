from dataclasses import dataclass
from telegram import Message
from multiprocessing.pool import ApplyResult
from typing import Union
from datetime import datetime


@dataclass
class BroadcastStats:
    n_job: int
    n_success: int
    n_failed: int

    def __add__(self, other: "BroadcastStats") -> "BroadcastStats":
        return BroadcastStats(
            self.n_job + other.n_job,
            self.n_success + other.n_success,
            self.n_failed + other.n_failed
        )

    def __str__(self):
        return f"Expect to send {self.n_job} subscribers, {self.n_success} successes and {self.n_failed} failed."


@dataclass
class JobSentInformation:
    id: int
    name: str
    result: Union[ApplyResult[Message | str], Message | str]

    def to_tuple(self) -> tuple[int, str, Union[ApplyResult[Message | str], Message | str]]:
        return self.id, self.name, self.result

    def dump(self) -> str:
        """
        Dump the JobSentInformation to a JSON formatted string.
        """
        template: str = '"id": "{id}", "name": "{name}", "result": "{result}"'
        content_string = template.format(id=self.id, name=self.name, result=self.result)
        return "{" + content_string + "}"
