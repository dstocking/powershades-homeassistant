import logging
import socket
import struct
import time
import asyncio
from homeassistant.components import network

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 42
BROADCAST_IP = "255.255.255.255"
GET_SERIAL_OPCODE = 0x00
GET_DEVICE_NAME_OPCODE = 0x3A
GET_SHADE_NAME_OPCODE = 0x34

# Discovery settings
DISCOVERY_TIMEOUT = 5.0
DISCOVERY_RETRIES = 2
DEVICE_NAME_TIMEOUT = 2.0

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


def crc16_xmodem(data: bytes) -> int:
    """Calculate CRC16-XMODEM checksum."""
    crc = 0
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ CrcTable[((crc >> 8) ^ b) & 0xFF]
    return crc


def build_get_serial_packet(sequence=0x01, channel=0x00):
    """Build Get Serial Number packet."""
    length = 0
    op = GET_SERIAL_OPCODE
    reserved = 0
    crc_data = struct.pack('<BBBB', op, sequence, channel, reserved)
    crc = crc16_xmodem(crc_data)
    packet = struct.pack('<HHBBBB', length, crc, op,
                         sequence, channel, reserved)
    return packet


def build_get_device_name_packet(sequence=0x01, channel=0x00):
    """Build Get Device Name packet for RF Gateway and channels."""
    length = 0
    op = GET_DEVICE_NAME_OPCODE
    reserved = 0
    crc_data = struct.pack('<BBBB', op, sequence, channel, reserved)
    crc = crc16_xmodem(crc_data)
    packet = struct.pack('<HHBBBB', length, crc, op,
                         sequence, channel, reserved)
    return packet


def build_get_shade_name_packet(sequence=0x01, channel=0x00):
    """Build Get PoE Shade Name packet."""
    length = 1  # 1 byte payload for Get/Set flag
    op = GET_SHADE_NAME_OPCODE
    reserved = 0
    get_set = 0  # 0 = Get, 1 = Set
    crc_data = struct.pack('<BBBBB', op, sequence, channel, reserved, get_set)
    crc = crc16_xmodem(crc_data)
    packet = struct.pack('<HHBBBBB', length, crc, op,
                         sequence, channel, reserved, get_set)
    return packet


def parse_serial_reply(data: bytes):
    """Parse Get Serial Number reply packet."""
    # See protocol doc for offsets
    if len(data) < 24:
        return None
    length, crc, op, seq, channel, reserved = struct.unpack(
        '<HHBBBB', data[:8])
    model = data[8]
    serial_low = struct.unpack('<I', data[12:16])[0]
    serial_high = struct.unpack('<I', data[16:20])[0]
    ip_bytes = data[24:28]
    ip_addr = '.'.join(str(b) for b in ip_bytes[::-1])
    return {
        'model': model,
        'serial': (serial_high << 32) | serial_low,
        'ip': ip_addr,
        'raw': data
    }


def parse_device_name_reply(data: bytes):
    """Parse Get Device Name reply packet."""
    if len(data) < 58:  # 8 bytes header + 50 bytes device name
        return None
    length, crc, op, seq, channel, reserved = struct.unpack(
        '<HHBBBB', data[:8])
    device_name_bytes = data[8:58]
    # Remove null bytes and decode
    device_name = device_name_bytes.split(b'\x00')[0].decode(
        'ascii', errors='ignore').strip()
    return {
        'device_name': device_name,
        'channel': channel,
        'raw': data
    }


def parse_shade_name_reply(data: bytes):
    """Parse Get PoE Shade Name reply packet."""
    if len(data) < 59:  # 8 bytes header + 1 byte get/set + 50 bytes device name
        return None
    length, crc, op, seq, channel, reserved, get_set = struct.unpack(
        '<HHBBBBB', data[:9])
    device_name_bytes = data[9:59]
    # Remove null bytes and decode
    device_name = device_name_bytes.split(b'\x00')[0].decode(
        'ascii', errors='ignore').strip()
    return {
        'device_name': device_name,
        'get_set': get_set,
        'raw': data
    }


async def async_discover_devices(hass, timeout=DISCOVERY_TIMEOUT):
    """Discover PowerShades devices on the network using UDP broadcast."""
    _LOGGER.info("Starting PowerShades device discovery...")

    adapters = await network.async_get_adapters(hass)
    packet = build_get_serial_packet()
    discovered = []
    sockets = []

    # Create sockets for each enabled network adapter
    for adapter in adapters:
        if not adapter["enabled"]:
            continue
        for ip_info in adapter["ipv4"]:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(1.0)  # Shorter timeout for individual reads
                sock.bind((ip_info["address"], 0))
                sockets.append(sock)
                _LOGGER.debug(f"Bound socket to {ip_info['address']}")
            except Exception as e:
                _LOGGER.warning(
                    f"Failed to bind socket to {ip_info['address']}: {e}")
                continue

    if not sockets:
        _LOGGER.warning("No network adapters available for discovery")
        return discovered

    # Send broadcast packets
    for sock in sockets:
        try:
            sock.sendto(packet, (BROADCAST_IP, UDP_PORT))
            _LOGGER.debug(f"Sent discovery packet from {sock.getsockname()}")
        except Exception as e:
            _LOGGER.warning(f"Failed to send discovery packet: {e}")

    # Listen for responses
    start_time = time.time()
    seen_devices = set()  # Track unique devices by IP

    while time.time() - start_time < timeout:
        for sock in sockets:
            try:
                data, addr = sock.recvfrom(256)
                if addr[0] not in seen_devices:
                    parsed = parse_serial_reply(data)
                    if parsed:
                        parsed['host'] = addr[0]
                        discovered.append(parsed)
                        seen_devices.add(addr[0])
                        _LOGGER.info(f"Discovered device: {parsed['ip']} "
                                     f"(Serial: {parsed['serial']})")
            except socket.timeout:
                continue
            except Exception as e:
                _LOGGER.debug(f"Error reading from socket: {e}")
                continue

    # Clean up sockets
    for sock in sockets:
        try:
            sock.close()
        except Exception:
            pass

    _LOGGER.info(f"Discovery complete. Found {len(discovered)} devices")
    return discovered


async def async_get_device_name(hass, ip_address, timeout=DEVICE_NAME_TIMEOUT):
    """Get device name from a PowerShades device with retry logic."""
    _LOGGER.debug(f"Getting device name from {ip_address}")

    for attempt in range(2):  # Try twice
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)

            # Try PoE Shade name command first (most common)
            packet = build_get_shade_name_packet()
            sock.sendto(packet, (ip_address, UDP_PORT))

            try:
                data, addr = sock.recvfrom(256)
                parsed = parse_shade_name_reply(data)
                if parsed and parsed['device_name']:
                    sock.close()
                    _LOGGER.debug(
                        f"Got PoE shade name: {parsed['device_name']}")
                    return parsed['device_name']
            except socket.timeout:
                pass

            # If PoE shade name failed, try RF Gateway device name
            packet = build_get_device_name_packet()
            sock.sendto(packet, (ip_address, UDP_PORT))

            try:
                data, addr = sock.recvfrom(256)
                parsed = parse_device_name_reply(data)
                if parsed and parsed['device_name']:
                    sock.close()
                    _LOGGER.debug(
                        f"Got RF gateway name: {parsed['device_name']}")
                    return parsed['device_name']
            except socket.timeout:
                pass

        except Exception as e:
            _LOGGER.debug(f"Error getting device name from {ip_address} "
                          f"(attempt {attempt + 1}): {e}")
        finally:
            try:
                sock.close()
            except Exception:
                pass

        if attempt < 1:  # Wait before retry
            await asyncio.sleep(0.1)

    _LOGGER.debug(f"Could not get device name from {ip_address}")
    return None


async def async_verify_device(hass, ip_address, timeout=2.0):
    """Verify that a device is a PowerShades device by sending a serial request."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        packet = build_get_serial_packet()
        sock.sendto(packet, (ip_address, UDP_PORT))

        try:
            data, addr = sock.recvfrom(256)
            parsed = parse_serial_reply(data)
            if parsed and parsed['ip'] == ip_address:
                sock.close()
                return parsed
        except socket.timeout:
            pass
        finally:
            sock.close()
    except Exception as e:
        _LOGGER.debug(f"Error verifying device {ip_address}: {e}")

    return None
