"""The test suite must fail closed at external I/O boundaries."""
import socket

import keyring
import pytest


def test_accidental_dns_is_rejected():
    with pytest.raises(pytest.fail.Exception, match='Unexpected network access'):
        socket.getaddrinfo('example.invalid', 443)


def test_accidental_connections_are_rejected():
    with socket.socket() as connection:
        with pytest.raises(pytest.fail.Exception, match='Unexpected network access'):
            connection.connect(('127.0.0.1', 1))


def test_tests_cannot_read_system_credentials():
    assert keyring.get_password('highright', 'gemini_api_key') is None
