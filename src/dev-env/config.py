from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator


class Proton(BaseModel):
    aliases: Annotated[list[str], Field(min_length=1)] | None = None
    id: Annotated[int, Field(ge=1)]
    path: str | None = None
    key: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_aliases(self) -> Self:
        """
        Interpret alias from key if not provided
        :return:
        """

        if self.aliases is None:
            self.aliases = [self.key.replace("_", "-")]
        return self

    @model_validator(mode="after")
    def validate_install_directory(self) -> Self:
        """
        Interpret install directory from key if not provided
        :return:
        """

        if self.path is None:
            self.path = self.key
        return self


class Config(BaseModel):
    apps: dict[str, int]
    protons: list[Proton]
