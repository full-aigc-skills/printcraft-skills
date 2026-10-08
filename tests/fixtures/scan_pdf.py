"""原创 RGB 栅格的无文本 PDF 夹具，CC0，无外部字体。"""
from pathlib import Path
import zlib


def make_scan(path, width, height, rgb):
    image = zlib.compress(rgb)
    content = b'q\n612 0 0 792 0 0 cm\n/Scan Do\nQ\n'
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /XObject << /Scan 4 0 R >> >> /Contents 5 0 R >>',
        f'<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(image)} >>\nstream\n'.encode() + image + b'\nendstream',
        f'<< /Length {len(content)} >>\nstream\n'.encode() + content + b'endstream',
    ]
    data = b'%PDF-1.4\n'
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    start = len(data)
    data += b'xref\n0 6\n0000000000 65535 f \n'
    for offset in offsets:
        data += f'{offset:010d} 00000 n \n'.encode()
    data += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    Path(path).write_bytes(data)
