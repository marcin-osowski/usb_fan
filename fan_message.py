
import font_8by8


class FanDeviceMessage(object):

  class Column(object):
    """Pixels should be a string of 0s and 1s, where 0 is off and 1 is on."""

    # Notes from reverse engineering the protocol.
    # Bytes are transformed with (0xa4-x)

    # Full empty line:         0x84a4
    # One bottom red pixel:    0x80a4
    # Second from the bottom:  0x82a4
    # Two bottom red pixels:   0x7ea4
    # Third from the bottom:   0x83a4
    # Three bottom red pixels: 0x7da4
    # Fourth from the bottom:  0x8424
    # Four bottom red pixels:  0x7d24

    # One top red pixel:       0x84a3
    # Second from the top:     0x84a2
    # Two top red pixels:      0x84a1
    # Third from the top:      0x84a0
    # Three top red pixels:    0x849d
    # Full red line:           0x7da5

    # Empty green line:        0x24a4
    # Full green line:         0x1da5

    # Empty blue line:         0x64a4
    # One bottom blue pixel:   0x60a4
    # Second from the bottom:  0x62a4
    # Full blue line:          0x5da5

    # Empty yellow line:       0x04a4
    # One bottom yellow pixel: 0x00a4
    # Full yellow line:        0xfda5

    # Empty white line:        0xc4a4
    # Full white line:         0xbda5

    def __init__(self, red=False, green=False, blue=False, pixels='0'*11):
      assert len(pixels) == 11
      assert all([pixel in ['0', '1'] for pixel in pixels])
      self.red = red
      self.green = green
      self.blue = blue
      self.pixels = pixels

    def serialize(self) -> bytes:
      # Binary format for the line (two bytes):
      # 00100  00100000000
      # GBR--  11 PIXELS
      line = []
      line.append('1' if self.green else '0')
      line.append('1' if self.blue else '0')
      line.append('1' if self.red else '0')
      line.append('00')
      # Invert the order of the pixels. The device expects
      # the pixels to be in reverse order.
      line.append(self.pixels[::-1])
      line = ''.join(line)
      return int(line, 2).to_bytes(2, byteorder='big')

    @staticmethod
    def deserialize(data: bytes):
      assert len(data) == 2
      data = int.from_bytes(data, byteorder='big')
      line = f"{data:016b}"
      green = line[0] == '1'
      blue = line[1] == '1'
      red = line[2] == '1'
      pixels = line[5:]
      # Invert the order of the pixels. The device expects
      # the pixels to be in reverse order.
      pixels = pixels[::-1]
      return FanDeviceMessage.Column(red, green, blue, pixels)

    def __str__(self) -> str:
      # Print the color, then the pixels
      color_str = [
        'R' if self.red else '-',
        'G' if self.green else '-',
        'B' if self.blue else '-',
      ]
      color_str = ''.join(color_str)
      return "Column(color={}: {})".format(color_str, self.pixels)


  def __init__(self, columns=None):
    if not columns:
      columns = []
    self.columns = columns

  def __str__(self) -> str:
    return f"FanDeviceMessage(num_columns={len(self.columns)})"

  def _generate_header(self) -> bytes:
    header = b'\x00\x81'
    header += (len(self.columns) + 2).to_bytes(2, 'little')
    header += b'\x00\x00'
    header += b'\x00\x00'
    return header

  @staticmethod
  def _encode_bytes(data : bytes):
    """Encode bytes as expected by the device.

    For some reason, the device expects the bytes to be inverted and shifted by 0xa4.
    """
    result = []
    for c in data:
      result.append((0x1a4 - c) & 0xff)
    return bytes(result)

  @staticmethod
  def _decode_bytes(data : bytes):
    """Decoding is the same as encoding."""
    return FanDeviceMessage._encode_bytes(data)

  def visualize(self, max_width=80) -> str:
    result = []

    # Add pixels
    for pixel_row in range(11):
      row = []
      for column in self.columns:
        pixel = 'X' if column.pixels[pixel_row] == '1' else ' '
        row.append(pixel)
      result.append("".join(row))

    # Add RGB information
    row_R = []
    row_G = []
    row_B = []
    for column in self.columns:
      row_R.append('R' if column.red else '-')
      row_G.append('G' if column.green else '-')
      row_B.append('B' if column.blue else '-')
    result.append("".join(row_R))
    result.append("".join(row_G))
    result.append("".join(row_B))

    for i in range(len(result)):
      row = result[i]
      if len(row) > max_width - 2:
        row = row[:max_width - 2]
        row += " …"
        result[i] = row

    result = "\n".join(result)
    result = f"Header: {self._generate_header().hex(' ')}\n" + result
    return result

  def add_characters_8by8_font(self, chars : bytes, red=False, green=False, blue=False):
    """Add an ASCII string of characters to the message.

    Don't forget to set at least one of the principal colors to see anything.
    """
    for c in chars:
      rows_numeric = font_8by8.FONT_8BY8[c]
      rows_string = [f"{row:08b}" for row in rows_numeric]
      # This is now 8 rows, but we need 11.
      # Pad with two rows on top, and one row
      # at the bottom.
      pad = ["0"*8]
      rows_string = pad + rows_string + pad + pad
      columns = ["" for i in range(8)]
      for row in range(11):
        for column in range(8):
          columns[column] += rows_string[row][column]
      
      for column in columns:
        self.columns.append(FanDeviceMessage.Column(pixels=column, red=red, green=green, blue=blue))

  @staticmethod
  def deserialize(data: bytes):
    assert len(data) > 8
    data = FanDeviceMessage._decode_bytes(data)
    header = data[:8]
    num_columns = int.from_bytes(header[2:4], 'little') - 2
    columns = []
    for i in range(num_columns):
      pos = 8 + (2 * i)
      one_column_data = data[pos:pos+2]
      column = FanDeviceMessage.Column.deserialize(one_column_data)
      columns.append(column)
    # Column data is inverted.
    columns = columns[::-1]

    msg = FanDeviceMessage(columns=columns)
    generated_header = msg._generate_header()
    if header != generated_header:
      print("Warning - generated header does not match the deserialized header.")
      print("This is likely due to un-implemented features of the protocol.")
      print("The header is not fully implemented at all.")
      print(f"Parsed header:    {header.hex(' ')}")
      print(f"Generated header: {generated_header.hex(' ')}")

    return msg

  def serialize(self) -> bytes:
    msg = [self._generate_header()]
    for column in self.columns[::-1]:
      msg.append(column.serialize())
    msg = b''.join(msg)
    return FanDeviceMessage._encode_bytes(msg)


