#!/usr/bin/env python3

import fan_device
import fan_message

import sys

def main():
  print("Example message:")
  msg = fan_message.FanDeviceMessage()
  msg.add_characters_8by8_font(b'I am not ', green=True)
  msg.add_characters_8by8_font(b'BMO', red=True)
  msg.add_characters_8by8_font(b', I am ', green=True)
  msg.add_characters_8by8_font(b'Football!', red=True, green=True, blue=True)
  print(msg.visualize())

  try:
    print("Uploading the message ...")
    dev = fan_device.connect()
    fan_device.send_message(dev, msg.serialize())
    print("Done.")
  except fan_device.USBFanDeviceError as e:
    print("Error:", e)
    sys.exit(1)


if __name__ == "__main__":
    main()

