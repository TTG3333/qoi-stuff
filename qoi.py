from PIL import Image
import os
os.chdir(os.path.dirname(__file__))

def decoder(filename):
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
        elif data[firstByte] // 64 == 3: # Run
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


def encoder(filename):
    img = Image.open(filename, "r")

decoder("dice.qoi")