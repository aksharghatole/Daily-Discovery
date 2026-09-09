"""Verified related-topic exploration using Wikipedia links."""

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

from providers.base import ProviderItem, ProviderUnavailable


class RelatedTopicProvider(Protocol):
    def get_item(self, title: str) -> ProviderItem: ...
    def related_titles(self, title: str, limit: int = 6) -> list[str]: ...


@dataclass(frozen=True)
class TopicNode:
    title: str
    summary: str
    source_url: str
    depth: int


@dataclass(frozen=True)
class TopicGraph:
    root: TopicNode
    related: tuple[TopicNode, ...]


class RabbitHoleService:
    """Build a shallow, source-linked topic graph without generated claims."""

    def __init__(self, provider: RelatedTopicProvider):
        self.provider = provider

    def explore(self, title: str, limit: int = 6) -> TopicGraph:
        root_item = self.provider.get_item(title.strip())
        root = self._node(root_item, depth=0)
        related: list[TopicNode] = []
        try:
            titles = self.provider.related_titles(root.title, limit=limit)
        except ProviderUnavailable:
            titles = []
        for related_title in titles:
            if related_title.casefold() == root.title.casefold():
                continue
            try:
                related.append(self._node(self.provider.get_item(related_title), depth=1))
            except ProviderUnavailable:
                continue
        return TopicGraph(root=root, related=tuple(related))

    @staticmethod
    def _node(item: ProviderItem, depth: int) -> TopicNode:
        return TopicNode(
            title=item.title,
            summary=item.content,
            source_url=item.source_url or f"https://en.wikipedia.org/wiki/{quote(item.title)}",
            depth=depth,
        )