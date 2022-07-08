#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dmxgrad import *

if __name__ == '__main__':
    img = Image.open('gradient2.png')

    rgb = GenGradGen(cycle=Cycle.REPEAT)

    for c in range(3):
        rgb.add_subgen(ImageGradGen(image=img, channel=c))

    class MySender(GradSender):
        def display(self, values):
            print('\r%s\033[K' % (', '.join(map(lambda v: '%.2x' % v, values))))

    sender = MySender(1, rgb, img.width, 250)
    print(sender)
    sender.run()
    print(sender.lastState.Succeeded() if sender.lastState is not None else '?')
