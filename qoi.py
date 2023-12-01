from PIL import Image
import os
os.chdir(os.path.dirname(__file__))

def decoder(filename: str) -> None:
    with open(filename, "rb") as F:
        data = F.read()
    if data[:4] != b"qoif":
        raise ValueError("The file provided is not a QOI image")
    width = int.from_bytes(data[4:8], "big")
    height = int.from_bytes(data[8:12], "big")
    if data[12] == 3:
        img = Image.new("RGB", (width, height))
    elif data[12] == 4:
        img = Image.new("RGBA", (width, height))
    else:
        raise ValueError("The colour channel count isn't valid")
    previous = [{"r": 0, "g": 0, "b": 0, "a": 0} for _ in range(64)]
    current = {"r": 0, "g": 0, "b": 0, "a": 255}
    pos = (current["r"] * 3 + current["g"] * 5 + current["b"] * 7 + current["a"] * 11) % 64
    previous[pos] = dict(current)
    firstByte = 14
    pixelCount = 0
    
    while True:
        if data[firstByte] == 0:
            if data[firstByte: firstByte + 8] == bytes([0, 0, 0, 0, 0, 0, 0, 1]):
                break
        if data[firstByte] == 254: # RGB
            r, g, b = [data[firstByte + i] for i in range(1, 4)]
            current = {"r": r, "g": g, "b": b, "a": current["a"]}
            if img.mode == "RGB":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"]))
            elif img.mode == "RGBA":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 4
            pixelCount += 1
        elif data[firstByte] == 255: # RGBA
            r, g, b, a = [data[firstByte + i] for i in range(1, 5)]
            current = {"r": r, "g": g, "b": b, "a": a}
            if img.mode == "RGB":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"]))
            elif img.mode == "RGBA":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 5
            pixelCount += 1
        elif data[firstByte] >> 6 == 0: # Index
            val = data[firstByte] & 63
            current = dict(previous[val])
            if img.mode == "RGB":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"]))
            elif img.mode == "RGBA":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 1
            pixelCount += 1
        elif data[firstByte] >> 6 == 1: # Diff
            rDelta = ((data[firstByte] & 48) >> 4) - 2
            gDelta = ((data[firstByte] & 12) >> 2) - 2
            bDelta = (data[firstByte] & 3) - 2
            current["r"] = (current["r"] + rDelta) % 256
            current["g"] = (current["g"] + gDelta) % 256
            current["b"] = (current["b"] + bDelta) % 256
            if img.mode == "RGB":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"]))
            elif img.mode == "RGBA":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 1
            pixelCount += 1
        elif data[firstByte] >> 6 == 2: # Luma
            gDelta = (data[firstByte] & 63) - 32
            rDelta = (data[firstByte + 1] >> 4) - 8 + gDelta
            bDelta = (data[firstByte + 1] & 15) - 8 + gDelta
            current["r"] = (current["r"] + rDelta) % 256
            current["g"] = (current["g"] + gDelta) % 256
            current["b"] = (current["b"] + bDelta) % 256
            if img.mode == "RGB":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"]))
            elif img.mode == "RGBA":
                img.putpixel((pixelCount % width, pixelCount // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 2
            pixelCount += 1
        elif data[firstByte] >> 6 == 3: # Run
            count = (data[firstByte] & 63) + 1
            for i in range(count):
                if img.mode == "RGB":
                    img.putpixel(((pixelCount + i) % width, (pixelCount + i) // width), (current["r"], current["g"], current["b"]))
                elif img.mode == "RGBA":
                    img.putpixel(((pixelCount + i) % width, (pixelCount + i) // width), (current["r"], current["g"], current["b"], current["a"]))
            firstByte += 1
            pixelCount += count
            continue
        else:
            raise ValueError(f"Unexpected byte at byte {firstByte}")
        pos = (current["r"] * 3 + current["g"] * 5 + current["b"] * 7 + current["a"] * 11) % 64
        previous[pos] = dict(current)
    
    img.save(filename + ".png")
    img.close()


def encoder(filename: str) -> None:
    img = Image.open(filename, "r")
    if img.mode[:-1] in "aA": # Only the colour formats with an alpha channel end with an a
        img.convert("RGBA")
    else:
        img.convert("RGB")
    data = bytearray(b"qoif")
    width, height = img.size
    data.extend(width.to_bytes(4, "big"))
    data.extend(height.to_bytes(4, "big"))
    if img.mode == "RGBA":
        data.append(4)
    if img.mode == "RGB":
        data.append(3)
    else:
        raise ValueError("The colour channel count isn't valid")
    data.append(0)
    previous = [[0]*4 for _ in range(64)]
    prev = [0, 0, 0, 255]
    current = [0, 0, 0, 255]
    pos = (prev[0] * 3 + prev[1] * 5 + prev[2] * 7 + prev[3] * 11) % 64
    previous[pos] = list(prev)
    pixelCount = 0
    
    while pixelCount < width * height:
        current = list(img.getpixel((pixelCount % width, pixelCount // width)))
        if current == prev: # Run
            for i in range(62):
                if pixelCount + i >= width * height:
                    i -= 1
                    break
                if list(img.getpixel(((pixelCount + i) % width, (pixelCount + i) // width))) != prev:
                    i -= 1
                    break
            data.append(192 + i)
            pixelCount += i
        elif current in previous: # Index
            data.append(previous.index(current))
        else: # get the r, g, b, a deltas, convert the r, g, b deltas from [-255, 255] to [-127, 127]
            r, g, b, a = (current[0] - prev[0]) % 256, (current[1] - prev[1]) % 256, (current[2] - prev[2]) % 256, current[3] - prev[3]
            r -= 256 if r >= 128 else 0
            g -= 256 if g >= 128 else 0
            b -= 256 if b >= 128 else 0
            if r >= -2 and r <= 1 and g >= -2 and g <= 1 and b >= -2 and b <= 1 and a == 0: # Diff
                data.append(64 + ((r + 2) << 4) + ((g + 2) << 2) + (b + 2))
            elif g >= -32 and g <= 31 and r - g >= -8 and r - g <= 7 and b - g >= -8 and b - g <= 7 and a == 0: # Luma
                data.extend([160 + g, ((r - g + 8) << 4) + (b - g + 8)])
            elif a == 0: # RGB
                data.extend([254, *current[:3]])
            else: # RGBA
                data.extend([255, *current])
        pos = (current[0] * 3 + current[1] * 5 + current[2] * 7 + current[3] * 11) % 64
        previous[pos] = list(current)
        prev = list(current)
        pixelCount += 1
    
    data.extend([0, 0, 0, 0, 0, 0, 0, 1])
    img.close()
    with open(filename + ".qoi", "bw") as F:
        F.write(data)