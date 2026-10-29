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
    def __init__(self, address, sender="sender", partial_match=False):
        self.address = address
        self.sender = sender
        self.partial_match = partial_match
        self.handled = []

    async def handle(self, details):
        self.handled.append(details)


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
            [("a@example.com", "FakeHandler", False), ("", "FakeHandler", False)],
        )

    def test_handler_addresses_marks_partial_match_handlers(self):
        process = GmailProcess(lambda: FakeApi(FakeMessagesResource()))
        process.set_handler(FakeHandler("@example.com", partial_match=True))

        self.assertEqual(process.handler_addresses(), [("@example.com", "FakeHandler", True)])


class GmailProcessFindHandlerTests(unittest.TestCase):
    def setUp(self):
        self.process = GmailProcess(lambda: FakeApi(FakeMessagesResource()))

    def register(self, address, partial_match=False):
        handler = FakeHandler(address, partial_match=partial_match)
        self.assertTrue(self.process.set_handler(handler))
        return handler

    def test_exact_match_requires_whole_address(self):
        handler = self.register("a@example.com")

        self.assertIs(self.process.find_handler("a@example.com"), handler)
        self.assertIsNone(self.process.find_handler("b@example.com"))
        self.assertIsNone(self.process.find_handler("xa@example.com"))

    def test_partial_match_finds_address_containing_pattern(self):
        handler = self.register("@example.com", partial_match=True)

        self.assertIs(self.process.find_handler("a@example.com"), handler)
        self.assertIs(self.process.find_handler("noreply@example.com"), handler)
        self.assertIsNone(self.process.find_handler("a@example.org"))

    def test_partial_match_ignores_case(self):
        handler = self.register("@Example.com", partial_match=True)

        self.assertIs(self.process.find_handler("A@EXAMPLE.COM"), handler)

    def test_exact_match_takes_priority_over_partial_match(self):
        self.register("@example.com", partial_match=True)
        exact = self.register("a@example.com")

        self.assertIs(self.process.find_handler("a@example.com"), exact)

    def test_longest_partial_match_wins(self):
        self.register("example.com", partial_match=True)
        specific = self.register("@mail.example.com", partial_match=True)

        self.assertIs(self.process.find_handler("a@mail.example.com"), specific)

    def test_empty_partial_match_is_rejected(self):
        self.assertFalse(self.process.set_handler(FakeHandler("", partial_match=True)))
        self.assertIsNone(self.process.find_handler("a@example.com"))

    def test_empty_exact_handler_does_not_match_every_address(self):
        self.register("")

        self.assertIsNone(self.process.find_handler("a@example.com"))


class GmailProcessProcessMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_message_calls_partial_match_handler(self):
        process = GmailProcess(lambda: FakeApi(FakeMessagesResource()))
        handler = FakeHandler("@example.com", partial_match=True)
        process.set_handler(handler)
        details = {"id": "msg-1", "from": "Example <noreply@example.com>"}
        process.get_mail_details = lambda msg_id: details

        await process.process_message("msg-1")

        self.assertEqual(handler.handled, [details])


if __name__ == "__main__":
    unittest.main()
