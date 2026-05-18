from types import SimpleNamespace

import pytest

from pynvdrs.umgpt import GPTClient, generate_response, parse_response


class MockCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"flag": true}'))]
        )


class MockClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=MockCompletions())


def test_gpt_client_generate_uses_underlying_client():
    client = MockClient()
    wrapper = GPTClient(client=client, model="gpt-test")

    response = wrapper.generate("system", "prompt", "narrative")

    assert response == '{"flag": true}'
    assert client.chat.completions.calls[0]["model"] == "gpt-test"


def test_generate_response_requires_model():
    with pytest.raises(ValueError):
        generate_response(MockClient(), "system", "prompt", "narrative", model=None)


def test_gpt_client_without_client_raises():
    with pytest.raises(ValueError):
        GPTClient().generate("system", "prompt", "narrative")


def test_parse_response_coerces_expected_types():
    parsed, error = parse_response('{"flag": "yes", "count": "2"}', {"flag": "bool", "count": "int"})

    assert error is False
    assert parsed == {"flag": True, "count": 2}