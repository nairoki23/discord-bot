import asyncio
import unittest
from types import SimpleNamespace

from scripts.clear_commands import clear_targets, collect_targets


class FakeTree:
    """CommandTree の fetch_commands / clear_commands / sync だけを真似る。"""

    def __init__(self, registered):
        # キー: ギルド ID（グローバルは None）
        self.registered = registered
        self.cleared = []
        self.synced = []

    async def fetch_commands(self, *, guild=None):
        return self.registered.get(guild and guild.id, [])

    def clear_commands(self, *, guild):
        self.cleared.append(guild and guild.id)

    async def sync(self, *, guild=None):
        self.synced.append(guild and guild.id)
        self.registered[guild and guild.id] = []


def cmd(name):
    return SimpleNamespace(name=name)


def guild(id):
    return SimpleNamespace(id=id, name=f"g{id}")


class ClearCommandsTest(unittest.TestCase):
    def test_collect_skips_empty(self):
        tree = FakeTree({None: [cmd("ping")], 2: [cmd("secret")]})
        targets = asyncio.run(collect_targets(tree, [guild(1), guild(2)]))
        self.assertEqual(
            [(g and g.id, [c.name for c in cs]) for g, cs in targets],
            [(None, ["ping"]), (2, ["secret"])],
        )

    def test_collect_nothing(self):
        tree = FakeTree({})
        self.assertEqual(asyncio.run(collect_targets(tree, [guild(1)])), [])

    def test_clear_syncs_each_target(self):
        tree = FakeTree({None: [cmd("ping")], 2: [cmd("secret")]})
        targets = asyncio.run(collect_targets(tree, [guild(1), guild(2)]))
        asyncio.run(clear_targets(tree, targets))
        self.assertEqual(tree.cleared, [None, 2])
        self.assertEqual(tree.synced, [None, 2])
        self.assertEqual(asyncio.run(collect_targets(tree, [guild(1), guild(2)])), [])


if __name__ == "__main__":
    unittest.main()
