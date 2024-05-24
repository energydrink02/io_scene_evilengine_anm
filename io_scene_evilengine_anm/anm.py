from dataclasses import dataclass
from .file import *
from mathutils import Quaternion, Vector
from math import sqrt

class InvalidAnimation(Exception):
    "Invalid animation file -> FourCC != SKB1/1BKS"

@dataclass
class Keyframe:
    timeindex: int
    rot: Quaternion
    loc: Vector

    @classmethod
    def read(cls, file):
        timeindex = file.read_short()
        rot = Dequantize(file.read_short(4, signed=True))
        loc = Vector(file.read_short(3, signed=True))
        return cls(timeindex, Quaternion((rot[3], rot[0], rot[1], rot[2])), loc)
    
    def write(self, file):
        file.write_short(self.timeindex)
        rot = Quantize(self.rot)
        file.write_short((rot[1], rot[2], rot[3], rot[0]), signed=True)
        file.write_short((int(self.loc[0]), int(self.loc[1]), int(self.loc[2])), signed=True)

@dataclass
class Anim_V1:
    flags: int
    keyframes: list
    times: tuple
    offsets: list

    @classmethod
    def read(cls, file):
        magic = file.read(4).decode("ANSI")
        if magic == "SKB1":
            file.endian = "<"
        elif magic == "1BKS":
            pass
        else:
            raise InvalidAnimation
        
        flags = file.read_int()
        bonecount, timecount = file.read_short(2)
        keycount = file.read_int()
        scale = Vector(file.read_float(3))

        keyframes = [Keyframe.read(file) for _ in range(keycount)]
        for key in keyframes:
            key.loc *= scale

        times = file.read_float(timecount)
        offsets = [file.read_short(bonecount) for _ in range(timecount-1)]
        
        return cls(flags, keyframes, times, offsets)

    @classmethod
    def open(cls, path):
        with FileReader(path, "rb") as file:
            return cls.read(file)
        
    def write(self, file):
        magic = "1BKS" if file.endian == ">" else "SKB1"
        file.write(magic.encode())

        file.write_int(self.flags)
        file.write_short(len(self.offsets[0]))
        file.write_short(len(self.times))
        file.write_int(len(self.keyframes))

        scale = Vector((0, 0, 0))
        for key in self.keyframes:
            for i in range(3):
                scale[i] = max(scale[i], abs(key.loc[i]))
        scale /= 32767.0

        file.write_float(tuple(scale))

        for key in self.keyframes:
            key.loc = Vector((key.loc[i] / scale[i] for i in range(3)))
            key.write(file)

        file.write_float(self.times)
        
        for off in self.offsets:
            file.write_short(off)

        if file.tell() % 4 != 0:
            file.write(b"\xCD\xCD")

    def save(self, path, endian):
        with FileReader(path, "wb", endian) as file:
            return self.write(file)


######################################################################


@dataclass
class Keyframe_V2:
    frame: int
    tran_index: int
    rot: Quaternion

    @classmethod
    def read(cls, file):
        frame = file.read_short()
        tran_index = file.read_short()

        quat = Dequantize(file.read_short(3, signed=True))
        qw = sqrt(abs(1-(sum(_**2 for _ in quat))))
        if frame & 0x8000: qw = -qw
        return cls(frame, tran_index, Quaternion((qw, quat[0], quat[1], quat[2])))
    
    def write(self, file):
        if self.rot.w < 0:
            self.frame |= 0x8000
        file.write_short(self.frame)
        file.write_short(self.tran_index)
        file.write_short(Quantize(self.rot[1:]), signed=True)


@dataclass
class Anim_V2:
    keyframes: list
    times: list
    translate: list
    offsets: list

    @classmethod
    def read(cls, file):
        magic = file.read(4).decode()
        if magic == "SKB1":
            file.endian = "<"
        elif magic == "1BKS":
            pass
        else:
            raise InvalidAnimation
        
        file.read_int()
        bones_num, times_num, keys_num, tran_num = file.read_short(4)
        scale = Vector(file.read_float(3))

        keyframes = [Keyframe_V2.read(file) for _ in range(keys_num)]
        times = [_ / 30 for _ in file.read_short(times_num)]

        if times_num & 1:
            file.read_short()

        translate = [Vector(file.read_short(3, signed=True)) * scale for _ in range(tran_num)]

        if tran_num & 1:
            file.read_short()

        offsets = [file.read_short(bones_num) for _ in range(times_num - 1)]

        return cls(keyframes, times, translate, offsets)

    @classmethod
    def open(cls, path):
        with FileReader(path, "rb") as file:
            return cls.read(file)
        
    def write(self, file):
        magic = "1BKS" if file.endian == ">" else "SKB1"
        file.write(magic.encode())

        file.write_int(0)
        file.write_short(len(self.offsets[0]))
        file.write_short(len(self.times))
        file.write_short(len(self.keyframes))
        file.write_short(len(self.translate))

        scale = Vector((0, 0, 0))
        for tran in self.translate:
            for i in range(3):
                scale[i] = max(scale[i], abs(tran[i]))
        scale /= 32767.0

        file.write_float(tuple(scale))

        for key in self.keyframes:
            key.write(file)

        for time in self.times:
            file.write_short(time)
        
        if len(self.times) & 1:
            file.write_short(0xCDCD)

        for tran in self.translate:
            file.write_short(tuple(round(tran[i] / scale[i]) for i in range(3)), signed=True)

        if len(self.translate) & 1:
            file.write_short(0xCDCD)

        for off in self.offsets:
            file.write_short(off)

        if sum(len(off) for off in self.offsets) & 1:
            file.write_short(0xCDCD)

    def save(self, filepath, endian):
        with FileReader(filepath, "wb", endian) as file:
            return self.write(file)
        