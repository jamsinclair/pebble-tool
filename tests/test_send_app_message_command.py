"""
Tests for the SendAppMessageCommand.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from pebble_tool.commands.emucontrol import SendAppMessageCommand
from pebble_tool.exceptions import ToolError
from libpebble2.services.appmessage import Int32, Uint32, CString, ByteArray


class TestParsePair:
    """Tests for SendAppMessageCommand._parse_pair"""

    def test_int_decimal(self):
        key, value = SendAppMessageCommand._parse_pair("1:int=42")
        assert key == 1
        assert isinstance(value, Int32)
        assert value.value == 42

    def test_int_hex_key(self):
        key, value = SendAppMessageCommand._parse_pair("0x1:int=42")
        assert key == 1
        assert isinstance(value, Int32)
        assert value.value == 42

    def test_int_negative(self):
        key, value = SendAppMessageCommand._parse_pair("0x1:int=-10")
        assert key == 1
        assert isinstance(value, Int32)
        assert value.value == -10

    def test_uint(self):
        key, value = SendAppMessageCommand._parse_pair("0x3:uint=100")
        assert key == 3
        assert isinstance(value, Uint32)
        assert value.value == 100

    def test_string(self):
        key, value = SendAppMessageCommand._parse_pair("0x2:string=hello")
        assert key == 2
        assert isinstance(value, CString)
        assert value.value == "hello"

    def test_cstring(self):
        key, value = SendAppMessageCommand._parse_pair("0x2:cstring=world")
        assert key == 2
        assert isinstance(value, CString)
        assert value.value == "world"

    def test_bytes(self):
        key, value = SendAppMessageCommand._parse_pair("0x4:bytes=DEADBEEF")
        assert key == 4
        assert isinstance(value, ByteArray)
        assert value.value == bytes.fromhex("DEADBEEF")

    def test_string_with_equals_in_value(self):
        key, value = SendAppMessageCommand._parse_pair("0x5:string=foo=bar")
        assert key == 5
        assert isinstance(value, CString)
        assert value.value == "foo=bar"

    def test_string_type_is_case_insensitive(self):
        key, value = SendAppMessageCommand._parse_pair("1:INT=5")
        assert key == 1
        assert isinstance(value, Int32)
        assert value.value == 5

    def test_invalid_missing_equals(self):
        with pytest.raises(ToolError, match="Invalid key-value pair"):
            SendAppMessageCommand._parse_pair("0x1:int")

    def test_invalid_missing_colon(self):
        with pytest.raises(ToolError, match="Invalid key-value pair"):
            SendAppMessageCommand._parse_pair("0x1=42")

    def test_invalid_key(self):
        with pytest.raises(ToolError, match="Invalid key"):
            SendAppMessageCommand._parse_pair("notanint:int=42")

    def test_invalid_type(self):
        with pytest.raises(ToolError, match="Invalid type"):
            SendAppMessageCommand._parse_pair("0x1:float=3.14")

    def test_invalid_int_value(self):
        with pytest.raises(ToolError, match="Invalid int value"):
            SendAppMessageCommand._parse_pair("0x1:int=notanumber")

    def test_invalid_uint_value(self):
        with pytest.raises(ToolError, match="Invalid uint value"):
            SendAppMessageCommand._parse_pair("0x1:uint=notanumber")

    def test_invalid_bytes_value(self):
        with pytest.raises(ToolError, match="Invalid hex bytes value"):
            SendAppMessageCommand._parse_pair("0x1:bytes=ZZZZ")


class TestParseBytesFile:
    """Tests for SendAppMessageCommand._parse_bytes_file"""

    def test_reads_file_contents(self):
        data = b'\xDE\xAD\xBE\xEF'
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            path = f.name
        try:
            key, value = SendAppMessageCommand._parse_bytes_file("0x4={}".format(path))
            assert key == 4
            assert isinstance(value, ByteArray)
            assert value.value == data
        finally:
            os.unlink(path)

    def test_hex_key(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'\x01\x02')
            path = f.name
        try:
            key, value = SendAppMessageCommand._parse_bytes_file("0xFF={}".format(path))
            assert key == 255
        finally:
            os.unlink(path)

    def test_filepath_with_equals(self):
        """File paths containing '=' should be handled correctly."""
        data = b'\x00'
        with tempfile.NamedTemporaryFile(suffix='=test.bin', delete=False) as f:
            f.write(data)
            path = f.name
        try:
            key, value = SendAppMessageCommand._parse_bytes_file("1={}".format(path))
            assert key == 1
            assert value.value == data
        finally:
            os.unlink(path)

    def test_invalid_missing_equals(self):
        with pytest.raises(ToolError, match="Invalid --bytes-file entry"):
            SendAppMessageCommand._parse_bytes_file("0x1")

    def test_invalid_key(self):
        with pytest.raises(ToolError, match="Invalid key"):
            SendAppMessageCommand._parse_bytes_file("notanint=/some/path")

    def test_file_not_found(self):
        with pytest.raises(ToolError, match="Could not read bytes file"):
            SendAppMessageCommand._parse_bytes_file("0x1=/nonexistent/path/file.bin")
