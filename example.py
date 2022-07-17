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
import signal


def setup_sparkle_demo():
    sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM)

    for iname in range(1, 4):
        sparklegen.add_subgen(ImageGradGen(image=Image.open(f'example_sparkle{iname}.png')))

    seqgen = SequenceGenGradGen(mode=GradPosition.STOP)

    seqgen.add_subgen(ImageGradGen(image=Image.open('example_start.png')),
                      sparklegen,
                      ImageGradGen(image=Image.open('example_completion.png')))

    return seqgen


def demo_SineGradGen():
    ggen = SineGradGen(length=GradPosition.compute_length(1, GradSender.DEFAULT_TICK_INTERVAL),
                levels=(1.0, 1.0, 1.0),
                phase=(0.0, 0.33, 0.66),
                mode=GradPosition.REPEAT)

    return ggen


def demo_LineGradGen():
    return LineGradGen(length=GradPosition.compute_length(0.5, GradSender.DEFAULT_TICK_INTERVAL),
                channelsFrom=(0, 255, 0),
                channelsTo=(255, 0, 255),
                mode=GradPosition.REPEAT)


def demo_ImageGradGen():
    return ImageGradGen(image=Image.open('example_completion.png'))


def demo_SquareGradGen():
    dgen = ParallelGenGradGen()

    for i in range(3):
        dgen.add_subgen(SquareGradGen(phase=0.33 * i,
                            length=GradPosition.compute_length(1, GradSender.DEFAULT_TICK_INTERVAL)))

    return dgen


def demo_GenGradGen():
    sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM)

    for iname in range(1, 4):
        sgN = ImageGradGen(image=Image.open(f'example_sparkle{iname}.png'), mode=GradPosition.REPEAT)
        sparklegen.add_subgen(sgN)

    seqgen = SequenceGenGradGen(mode=GradPosition.STOP)

    seqgen.add_subgen(ImageGradGen(image=Image.open('example_start.png')),
                      sparklegen,
                      ImageGradGen(image=Image.open('example_completion.png')),
                      )

    return seqgen


def choose_demonstration():
    demos = (('SineGradGen', demo_SineGradGen),
             ('LineGradGen', demo_LineGradGen),
             ('ImageGradGen', demo_ImageGradGen),
             ('SquareGradGen', demo_SquareGradGen),
             ('GenGradGen', demo_GenGradGen),
             )

    print('DMXGRAD r%s demonstration:' % REVISION)

    dfunction = None
    for ix, (dname, _) in enumerate(demos, 1):
        print('%d. %s' % (ix, dname))

    try:
        dnum = int(input('Enter demonstration number, then press RETURN: '))

        if dnum >=1 and dnum <= len(demos):
            dfunc = demos[dnum - 1][1]
            print(dfunc)
            return dfunc()
    except Exception as ex:
        print(ex)
        return


def main():
    class MySender(GradSender):
        def display(self, values):
            print('\r%4s: %s\033[K' % (
                        '∞' if self.iterations is None else self.iterations,
                        ' '.join(map(lambda v: '%.2x' % v, values))),
                  end='')

    dgen = choose_demonstration()
    if not dgen:
        print('No demo choosen')
        return -1

    print(dgen)

    sender = MySender(generator=dgen)

    def __sigint_handler(sig, frame):
        sender.stop = True

    oldCC = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, __sigint_handler)

    print('Running demonstration, press Ctrl+C to stop')

    sender.run()
    signal.signal(signal.SIGINT, oldCC)

    print('\nlastState=%s' % (sender.lastState.Succeeded() if sender.lastState is not None else '?'))

    sender.blackout()
    print('\n***END***')


if __name__ == '__main__':
    main()
