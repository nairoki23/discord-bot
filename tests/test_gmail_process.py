import unittest
from unittest.mock import patch

from service.google.gmail.process import GmailProcess


class FakeRequest:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc

    def execute(self):
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeMessagesResource:
    def __init__(self, modify_exc=None):
        self.modify_exc = modify_exc
        self.modify_kwargs = None

    def modify(self, **kwargs):
        self.modify_kwargs = kwargs
        return FakeRequest(response={}, exc=self.modify_exc)


class FakeUsersResource:
    def __init__(self, messages_resource):
        self.messages_resource = messages_resource

    def messages(self):
        return self.messages_resource


class FakeApi:
    def __init__(self, modify_exc=None):
        self.messages_resource = FakeMessagesResource(modify_exc=modify_exc)
        self.users_resource = FakeUsersResource(self.messages_resource)

    def users(self):
        return self.users_resource


class GmailProcessMarkAsReadTests(unittest.TestCase):
    def test_mark_as_read_removes_unread_label(self):
        api = FakeApi()
        process = GmailProcess(lambda: api)

        result = process.mark_as_read("msg-1")

        self.assertTrue(result)
        self.assertEqual(
            api.messages_resource.modify_kwargs,
            {"userId": "me", "id": "msg-1", "body": {"removeLabelIds": ["UNREAD"]}},
        )

    def test_mark_as_read_returns_false_on_failure(self):
        api = FakeApi(modify_exc=Exception("boom"))
        process = GmailProcess(lambda: api)

        with patch("builtins.print"):
            result = process.mark_as_read("msg-1")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
