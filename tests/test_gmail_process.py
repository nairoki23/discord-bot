import unittest

from service.google.gmail.process import GmailProcess


class FakeMessagesResource:
    def __init__(self):
        self.modify_kwargs = None
        self.raise_on_modify = False

    def modify(self, **kwargs):
        self.modify_kwargs = kwargs
        return FakeRequest(raise_on_execute=self.raise_on_modify)


class FakeRequest:
    def __init__(self, raise_on_execute=False):
        self.raise_on_execute = raise_on_execute

    def execute(self):
        if self.raise_on_execute:
            raise RuntimeError("boom")
        return {}


class FakeUsersResource:
    def __init__(self, messages_resource):
        self.messages_resource = messages_resource

    def messages(self):
        return self.messages_resource


class FakeApi:
    def __init__(self, messages_resource):
        self.messages_resource = messages_resource

    def users(self):
        return FakeUsersResource(self.messages_resource)


class GmailProcessMarkAsReadTests(unittest.TestCase):
    def test_mark_as_read_removes_the_unread_label(self):
        messages_resource = FakeMessagesResource()
        process = GmailProcess(lambda: FakeApi(messages_resource))

        result = process.mark_as_read("msg-1")

        self.assertTrue(result)
        self.assertEqual(
            messages_resource.modify_kwargs,
            {"userId": "me", "id": "msg-1", "body": {"removeLabelIds": ["UNREAD"]}},
        )

    def test_mark_as_read_returns_false_on_failure(self):
        messages_resource = FakeMessagesResource()
        messages_resource.raise_on_modify = True
        process = GmailProcess(lambda: FakeApi(messages_resource))

        result = process.mark_as_read("msg-1")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
