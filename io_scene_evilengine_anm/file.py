import io
import struct

__all__ = ["FileReader", "Quantize", "Dequantize"]

class FileReader(io.FileIO):
    def __init__(self, filepath: str, mode: str, endian: str = ">"):
        super().__init__(filepath, mode)
        self.endian = endian

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()
        
    def read_int(self, num: int = 1, signed: bool = False) -> int | tuple[int]:
        value = struct.unpack("%s%d%s" % (self.endian, num, "i" if signed else "I"), self.read(4*num))
        return value[0] if num == 1 else value
    
    def read_short(self, num: int = 1, signed: bool = False) -> int | tuple[int]:
        value = struct.unpack("%s%d%s" % (self.endian, num, "h" if signed else "H"), self.read(2*num))
        return value[0] if num == 1 else value
    
    def read_float(self, num: int = 1) -> float | tuple[float]:
        value = struct.unpack("%s%df" % (self.endian, num), self.read(4*num))
        return value[0] if num == 1 else value
    
    def write_int(self, value, signed: bool = False) -> None:
        data = value if hasattr(value, "__len__") else (value, )
        self.write(struct.pack("%s%d%s" % (self.endian, len(data), "i" if signed else "I"), *data))

    def write_short(self, value, signed: bool = False) -> None:
        data = value if hasattr(value, "__len__") else (value, )
        self.write(struct.pack("%s%d%s" % (self.endian, len(data), "h" if signed else "H"), *data))

    def write_float(self, value) -> None:
        data = value if hasattr(value, "__len__") else (value, )
        self.write(struct.pack("%s%df" % (self.endian, len(data)), *data))


def Clamp16(value: int) -> int:
    return max(min(value, 32767), -32768)

def Quantize(value: int | tuple | list) -> tuple | int:
    if hasattr(value, "__len__"):
        return tuple(Clamp16(round(x * 32767)) for x in value)
    else:
        return Clamp16(round(value * 32767))
    
def Dequantize(value: int | tuple | list) -> tuple | int:
    if hasattr(value, "__len__"):
        return tuple(x / 32767 for x in value)
    else:
        return value / 32767
    