import struct
import time
import sys

from PS3MAPI import PS3MAPI

buttons = {
    1: "l2",
    2: "r2",
    4: "l1",
    8: "r1",
    16: "triangle",
    32: "circle",
    64: "cross",
    128: "square",
    256: "select",
    512: "l3",
    1024: "r3",
    2048: "start",
    4096: "up",
    8192: "right",
    16384: "down",
    32768: "left"
}


def down_buttons(mask: int) -> [str]:
    inputs = []

    for (i, input) in enumerate(buttons):
        if input & mask > 0:
            inputs.append(buttons[input])

    return inputs


api = PS3MAPI(sys.argv[1])
api.connect()
pid_list = api.get_pid_list()
api.notify("Input display connected!")

import sys, pygame
pygame.init()

size = width, height = 320, 240
speed = [2, 2]
black = 0, 0, 0

screen = pygame.display.set_mode(size)



while 1:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()

    time.sleep(0.01666667)

    buttonos = down_buttons(int.from_bytes(api.memory_get(pid_list[2], 0x964ae0, 4), "big"))
    analogs = api.memory_get(pid_list[2], 0x00964a40, 16)

    lx = struct.unpack('>f', analogs[8:12])[0]
    ly = struct.unpack('>f', analogs[12:16])[0]

    rx = struct.unpack('>f', analogs[0:4])[0]
    ry = struct.unpack('>f', analogs[4:8])[0]

    screen.fill((255, 255, 255))

    pygame.draw.circle(screen, (0, 0, 0), (190, 215), 15, 2)
    pygame.draw.circle(screen, (0, 0, 0) if "r3" not in buttonos else (255, 0, 0), (190+(rx*7.5), 215+(ry*7.5)), 15, 15)

    pygame.draw.circle(screen, (0, 0, 0), (105, 215), 15, 2)
    pygame.draw.circle(screen, (0, 0, 0) if "l3" not in buttonos else (255, 0, 0), (105 + (lx * 7.5), 215 + (ly * 7.5)), 15, 15)

    pygame.draw.circle(screen, (0, 0, 255) if "cross" not in buttonos else (0, 0, 0), (260, 220-20), 15, 15)  # cross
    pygame.draw.circle(screen, (255, 0, 0) if "circle" not in buttonos else (0, 0, 0), (290, 190-20), 15, 15)  # circle
    pygame.draw.circle(screen, (0, 255, 0) if "triangle" not in buttonos else (0, 0, 0), (260, 160-20), 15, 15)  # triangle
    pygame.draw.circle(screen, (251, 72, 196) if "square" not in buttonos else (0, 0, 0), (230, 190-20), 15, 15)  # square

    pygame.draw.rect(screen, (180, 180, 180) if "r1" not in buttonos else (0, 0, 0), (240, 120-20, 40, 15))
    pygame.draw.rect(screen, (180, 180, 180) if "r2" not in buttonos else (0, 0, 0), (240, 70-20, 40, 35))

    pygame.draw.rect(screen, (180, 180, 180) if "l1" not in buttonos else (0, 0, 0), (40, 120-20, 40, 15))
    pygame.draw.rect(screen, (180, 180, 180) if "l2" not in buttonos else (0, 0, 0), (40, 70-20, 40, 35))

    pygame.draw.rect(screen, (0, 0, 0) if "down" in buttonos and ly+lx == 0 else (180, 180, 180), (50, 200-20, 15, 25), 5, 5)
    pygame.draw.rect(screen,(0, 0, 0) if "right" in buttonos and lx+ly == 0 else (180, 180, 180), (65, 185-20, 25, 15), 5, 5)
    pygame.draw.rect(screen,(0, 0, 0) if "up" in buttonos and ly+lx == 0 else (180, 180, 180), (50, 160-20, 15, 25), 5, 5)
    pygame.draw.rect(screen,(0, 0, 0) if "left" in buttonos and lx+ly == 0 else (180, 180, 180), (25, 185-20, 25, 15), 5, 5)

    pygame.draw.rect(screen, (180, 180, 180) if "start" not in buttonos else (0, 0, 0), (170, 185-20, 25, 15))
    pygame.draw.rect(screen, (180, 180, 180) if "select" not in buttonos else (0, 0, 0), (105, 185-20, 25, 15))

    pygame.display.flip()