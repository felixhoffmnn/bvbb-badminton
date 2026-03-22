from pydantic import BaseModel


class Group(BaseModel):
    group_id: int
    name: str


class CategoryGroups(BaseModel):
    category: str
    groups: list[Group]


class Championship(BaseModel):
    code: str
    name: str
    categories: list[CategoryGroups]
