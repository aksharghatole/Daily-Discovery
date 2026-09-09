from providers.base import ProviderItem
from services.rabbit_hole_service import RabbitHoleService


class FakeRelatedProvider:
    def __init__(self):
        self.items = {
            "Black hole": "A region of spacetime with strong gravity.",
            "Event horizon": "A boundary beyond which light cannot escape.",
            "Hawking radiation": "Thermal radiation predicted for black holes.",
        }

    def get_item(self, title):
        return ProviderItem(
            title=title,
            content=self.items[title],
            source_name="Wikipedia",
            source_url=f"https://example.test/{title.replace(' ', '_')}",
        )

    def related_titles(self, title, limit=6):
        return ["Event horizon", "Black hole", "Hawking radiation"][:limit]


def test_rabbit_hole_builds_verified_shallow_graph():
    graph = RabbitHoleService(FakeRelatedProvider()).explore("Black hole")

    assert graph.root.title == "Black hole"
    assert [node.title for node in graph.related] == [
        "Event horizon",
        "Hawking radiation",
    ]
    assert all(node.depth == 1 and node.source_url for node in graph.related)