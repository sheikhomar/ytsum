import pytest


class TestHelloWorld:
    @pytest.fixture
    def hello_world_message(self) -> str:
        return "Hello, world!"

    def test_trivial(self, hello_world_message: str) -> None:
        assert hello_world_message == "Hello, world!"
