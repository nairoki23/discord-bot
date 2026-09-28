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
    def __init__(self, messages_resource, raise_on_get_profile=False):
        self.messages_resource = messages_resource
        self.raise_on_get_profile = raise_on_get_profile

    def messages(self):
        return self.messages_resource

    def getProfile(self, **kwargs):
        return FakeRequest(raise_on_execute=self.raise_on_get_profile)


class FakeApi:
    def __init__(self, messages_resource, raise_on_get_profile=False):
        self.messages_resource = messages_resource
        self.raise_on_get_profile = raise_on_get_profile

    def users(self):
        return FakeUsersResource(self.messages_resource, self.raise_on_get_profile)


class FakeHandler:
    def __init__(self, address, sender="sender"):
        self.address = address
        self.sender = sender


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


class GmailProcessVerifyConnectionTests(unittest.TestCase):
    def test_verify_connection_true_when_api_call_succeeds(self):
        process = GmailProcess(lambda: FakeApi(FakeMessagesResource()))

        self.assertTrue(process.verify_connection())

    def test_verify_connection_false_when_api_call_fails(self):
        process = GmailProcess(
            lambda: FakeApi(FakeMessagesResource(), raise_on_get_profile=True)
        )

        self.assertFalse(process.verify_connection())


class GmailProcessHandlerAddressesTests(unittest.TestCase):
    def test_handler_addresses_lists_every_registered_handler(self):
        process = GmailProcess(lambda: FakeApi(FakeMessagesResource()))
        process.set_handler(FakeHandler("a@example.com"))
        process.set_handler(FakeHandler(""))  # 素通し用ハンドラーの空アドレスも含む

        self.assertEqual(
            process.handler_addresses(),
            [("a@example.com", "FakeHandler"), ("", "FakeHandler")],
        )


if __name__ == "__main__":
    unittest.main()
