"""PowerShades UDP packet building and parsing.

Pure functions only — no sockets, no Home Assistant imports.

Packet layout (little-endian):
    Length(2) + CRC16-XMODEM(2) + Op(1) + Sequence(1) + Channel(1) + Reserved(1) + Payload
The CRC covers Op + Sequence + Channel + Reserved + Payload.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .const import OP_GET_STATUS

HEADER_SIZE = 8

CrcTable = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
]

# Get/Set flag payload for the Get PoE Shade Name command (0 = Get)
GET_SHADE_NAME_PAYLOAD = b"\x00"


def crc16_xmodem(data: bytes) -> int:
    """Calculate CRC16-XMODEM checksum."""
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ CrcTable[((crc >> 8) ^ b) & 0xFF]
    return crc


def build_packet(op: int, sequence: int = 0, channel: int = 0,
                 payload: bytes = b"") -> bytes:
    """Build a PowerShades UDP packet."""
    reserved = 0
    crc_data = struct.pack("<BBBB", op, sequence, channel, reserved) + payload
    crc = crc16_xmodem(crc_data)
    return struct.pack("<HHBBBB", len(payload), crc, op,
                       sequence, channel, reserved) + payload


def build_set_position_payload(percent: int) -> bytes:
    """Build the payload for a Set Position packet."""
    mask = 0x0001  # MASK_PERCENT
    tilt = 0
    channel_mask = 0
    return struct.pack("<HhhI", mask, percent, tilt, channel_mask)


def build_set_limit_payload(limit_type: int) -> bytes:
    """Build the payload for a Set Limit packet."""
    return struct.pack("<H", limit_type)


def build_set_name_payload(name: str) -> bytes:
    """Build the payload for a Set PoE Shade Name packet."""
    return b"\x01" + name.encode("ascii")[:50].ljust(50, b"\x00")


@dataclass(frozen=True)
class PacketHeader:
    """Parsed packet header."""

    length: int
    crc: int
    op: int
    sequence: int
    channel: int


def parse_header(data: bytes) -> PacketHeader | None:
    """Parse a packet header, or return None if too short."""
    if len(data) < HEADER_SIZE:
        return None
    length, crc, op, sequence, channel, _reserved = struct.unpack(
        "<HHBBBB", data[:HEADER_SIZE])
    return PacketHeader(length, crc, op, sequence, channel)


def verify_packet(data: bytes) -> bool:
    """Validate a packet's length field and CRC.

    The CRC covers Op + Sequence + Channel + Reserved + Payload for
    replies as well as commands (verified against real device replies).
    """
    header = parse_header(data)
    if header is None or len(data) < HEADER_SIZE + header.length:
        return False
    return crc16_xmodem(data[4:HEADER_SIZE + header.length]) == header.crc


def parse_serial_reply(data: bytes) -> dict | None:
    """Parse a Get Serial Number reply packet.

    Payload layout (after the 8-byte header): Model(1) Pad1(1) Pad2(1)
    Direction(1) SerialLow(4) SerialHigh(4) DhcpEnabled(1) IP(4)
    Subnet(4) Gateway(4) Internal(50).
    """
    if len(data) < 24:
        return None
    model = data[8]
    direction = data[11]
    serial_low = struct.unpack("<I", data[12:16])[0]
    serial_high = struct.unpack("<I", data[16:20])[0]
    dhcp_enabled = bool(data[20])
    return {
        "model": model,
        "direction": direction,
        "serial": (serial_high << 32) | serial_low,
        "dhcp_enabled": dhcp_enabled,
    }


def _decode_name(name_bytes: bytes) -> str | None:
    name = name_bytes.split(b"\x00")[0].decode("ascii", errors="ignore").strip()
    return name or None


def parse_device_name_reply(data: bytes) -> str | None:
    """Parse a Get Device Name (RF gateway) reply packet."""
    if len(data) < 58:  # 8-byte header + 50-byte name
        return None
    return _decode_name(data[8:58])


def parse_shade_name_reply(data: bytes) -> str | None:
    """Parse a Get PoE Shade Name reply packet."""
    if len(data) < 59:  # 8-byte header + 1-byte get/set flag + 50-byte name
        return None
    return _decode_name(data[9:59])


@dataclass(frozen=True)
class StatusReply:
    """Parsed status reply."""

    position: int | None
    battery_mv: int


def parse_status_reply(data: bytes) -> StatusReply | None:
    """Parse a Get Status reply packet."""
    header = parse_header(data)
    if header is None or header.op != OP_GET_STATUS:
        return None
    payload = data[HEADER_SIZE:HEADER_SIZE + header.length]
    if len(payload) < 30:
        return None
    (percent, _tilt, _memory, battery_mv, _time, _cycles, _stalls,
     _temperature, _raw_percent, _raw_tilt) = struct.unpack(
        "<hhHHIIIhII", payload[:30])
    # The device reports percent as signed; treat out-of-range as unknown
    position = percent if 0 <= percent <= 100 else None
    return StatusReply(position=position, battery_mv=battery_mv)


def battery_percentage(battery_mv: int | None) -> int | None:
    """Convert battery voltage (mV) to a rough percentage (3.0V=0%, 4.2V=100%)."""
    if battery_mv is None:
        return None
    voltage = battery_mv / 1000.0
    if voltage <= 3.0:
        return 0
    if voltage >= 4.2:
        return 100
    return int((voltage - 3.0) / (4.2 - 3.0) * 100)
