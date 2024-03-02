print("This program uses pyusb to communicate with a USB device.")
print("See the FAQ at https://github.com/pyusb/pyusb/blob/master/docs/faq.rst")
print("In particular make sure that you have system permissions to directly communicate with USB devices.")
print("")

import usb.core
import time

ID_VENDOR=0x1a86
ID_PRODUCT=0x5537

WRITE_ENDPOINT=0x02
READ_ENDPOINT=0x82

RESP_OK=bytes.fromhex("402480")
RESP_BAD=bytes.fromhex("402482")


class USBFanDeviceError(Exception):
  pass


def connect():
  """Connect to the device and return the device object."""
  dev = usb.core.find(idVendor=ID_VENDOR, idProduct=ID_PRODUCT)
  if dev is None:
    raise USBFanDeviceError("Device %04x:%04x not found" % (ID_VENDOR, ID_PRODUCT))
  print("Found device %04x:%04x" % (ID_VENDOR, ID_PRODUCT))

  try:
    manufacturer = dev.manufacturer
    product = dev.product
    print("Connected to %s %s" % (manufacturer, product))
  except:
    raise USBFanDeviceError("Failed to get device info. Do you have permission to access the device?")
  return dev


def send_packet(dev, data : bytes):
  """Send a single packet to the device and check the response."""
  if len(data) != 7:
    raise USBFanDeviceError("Data packet must be 7 bytes long")

  # Checksum is the sum of the first 7 bytes
  data_with_checksum = data + bytes([sum(data) & 0xFF])
  print("Writing %d bytes to the device: %s" % (len(data_with_checksum), data_with_checksum.hex()))
  dev.write(WRITE_ENDPOINT, data=data_with_checksum)

  # Read response
  resp = dev.read(READ_ENDPOINT, size_or_buffer=64)
  resp = bytes(resp)
  if resp != RESP_OK:
    if resp == RESP_BAD:
      raise USBFanDeviceError("Device responded with bad status after writing data. Is it not ready?")
    raise USBFanDeviceError("Device responded with unknown status after writing data: %s" % resp.hex())


def send_initial_packet(dev, data_size : int):
  """Send the initial packet to the device.

  This packet has a different format than the data packets.
  One should use send_message() to send the entire message.
  """
  if data_size <= 0:
    raise USBFanDeviceError("Data size must be positive")
  if data_size >= 0x2000:
    raise USBFanDeviceError("Data size too large")
  if data_size >= 0x1000:
    order_of_magnitude = 6
  elif data_size >= 0x800:
    order_of_magnitude = 5
  elif data_size >= 0x400:
    order_of_magnitude = 4
  elif data_size >= 0x200:
    order_of_magnitude = 3
  elif data_size >= 0x100:
    order_of_magnitude = 2
  else:
    order_of_magnitude = 1
  packet = bytes([
      0x40, 0x40,
      order_of_magnitude,
      data_size & 0xFF, (data_size >> 8) & 0xFF,
      0, 0,
  ])
  send_packet(dev, packet)


def send_data_packet(dev, data : bytes):
  """Send a single data packet to the device.

  Use send_message() to send the entire message.
  """
  if len(data) != 5:
    raise USBFanDeviceError("Data packet must be 5 bytes long")

  packet = bytes([0x40, 0x23]) + data
  send_packet(dev, packet)


def _send_message_fast(dev, msg : bytes):
  """Send a message to the device.

  The message is split into 5-byte packets and sent to the device.

  It is recommended to use send_message(), as it works around potential
  timing problems by waiting and sending data twice.
  """
  if len(msg) % 5 != 0:
    # Pad it with null bytes - using 0xa4 because that's null after conversion.
    msg += b'\xa4' * (5 - (len(msg) % 5))

  send_initial_packet(dev, len(msg))
  for i in range(0, len(msg), 5):
    send_data_packet(dev, msg[i:i+5])


def send_message(dev, msg : bytes):
  """Send a message to the device."""
  print("Sending message ...")
  time.sleep(1.0)
  _send_message_fast(dev, msg)
  print("Sending message again ...")
  time.sleep(1.0)
  _send_message_fast(dev, msg)
  time.sleep(1.0)


