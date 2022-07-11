#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" example.py

    Пример использования модуля dmxgrad.

    Copyright 2022 MC-6312

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>."""


from dmxgrad import *


if __name__ == '__main__':
    sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM)

    for iname in range(1, 4):
        sparklegen.add_subgen(ImageGradGen(image=Image.open(f'example_sparkle{iname}.png')))

    seqgen = SequenceGenGradGen(mode=GradPosition.STOP)

    seqgen.add_subgen(ImageGradGen(image=Image.open('example_start.png')),
                      sparklegen,
                      ImageGradGen(image=Image.open('example_completion.png')))

    class MySender(GradSender):
        def display(self, values):
            print('\r%4s: %s  %s\033[K' % (
                        '∞' if self.iterations is None else self.iterations,
                        ' '.join(map(lambda v: '%.2x' % v, values)),
                        self.generator.activeGen.name),
                  end='')

    sender = MySender(generator=seqgen, interval=50)

    print(sender)
    sender.run()
    print('\n', sender.lastState.Succeeded() if sender.lastState is not None else '?')
