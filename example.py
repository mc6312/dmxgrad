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
    sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM, name='sparkle_images')

    for iname in range(1, 4):
        fname = f'example_sparkle{iname}.png'
        sparklegen.add_subgen(ImageGradGen(image=Image.open(fname),
                              name='image="%s"' % fname))

    seqgen = SequenceGenGradGen(mode=GradPosition.STOP, name='sparkle_sequence')

    seqgen.add_subgen(ImageGradGen(image=Image.open('example_start.png'),
                                   name='sparkle_start_image'),
                      sparklegen,
                      ImageGradGen(image=Image.open('example_completion.png'),
                                   name='sparkle_end_image'))

    return seqgen


def demo_SineWaveGradGen():
    ggen = SineWaveGradGen(length='1',
                levels=(1.0, 1.0, 1.0),
                lowLevels=(0.0, 0.0, 0.5),
                phases=(0.0, 0.33, 0.66),
                periods=(1.0, 2.0, 3.0),
                mode=GradPosition.REPEAT,
                name='sine_wave')

    return ggen


def demo_EnvelopeGenGradGen():
    return EnvelopeGenGradGen(sourcegen=demo_NoiseGen(),
                              envelopegen=demo_LineGradGen(),
                              name='envelope')


def demo_LineGradGen():
    return LineGradGen(length=0.5,
                channelsFrom=(0, 1, 0),
                channelsTo=(1, 0, 1),
                mode=GradPosition.REPEAT,
                name='line')


def demo_ImageGradGen():
    return ImageGradGen(image=Image.open('example_completion.png'),
                        name='image')


def demo_SquareWaveGradGen():
    dgen = ParallelGenGradGen(name='parallel')

    for i in range(3):
        dgen.add_subgen(SquareWaveGradGen(phases=0.33 * i,
                            length='1',
                            mode=GradPosition.REPEAT,
                            name='square#%d' % i))

    return dgen


def demo_NoiseGen():
    return NoiseGen(minValues=(0.5, 0.5, 0.5),
                maxValues=(1.0, 1.0, 1.0),
                name='noise')


def demo_SequenceGenGradGen():
    sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM,
                    name='sparkle_sequence')

    for iname in range(1, 4):
        fname = f'example_sparkle{iname}.png'
        sgN = ImageGradGen(image=Image.open(fname),
                           mode=GradPosition.REPEAT,
                           name='image="%s"' % fname)
        sparklegen.add_subgen(sgN)

    seqgen = SequenceGenGradGen(mode=GradPosition.STOP,
        subgen=(ImageGradGen(image=Image.open('example_start.png'),
                             name='sparkle_begin'),
                sparklegen,
                ImageGradGen(image=Image.open('example_completion.png'),
                             name='sparkle_end')),
        name='sequence')

    return seqgen


def demo_CrossfadeGenGradGen():
    pausegen = ConstantGradGen(length=0.5, values=0, name='pause')

    def mksingen(n):
        return SineWaveGradGen(length=1.0, levels=(1,), phases=(0,),
                               mode=GradPosition.REPEAT,
                               name='sine#%d' % n)

    ch0gen = SequenceGenGradGen(subgen=(mksingen(1), pausegen, pausegen),
                mode=GradPosition.REPEAT,
                name='ch0seq')
    ch1gen = SequenceGenGradGen(subgen=(pausegen, mksingen(2), pausegen),
                mode=GradPosition.REPEAT,
                name='ch1seq')
    ch2gen = SequenceGenGradGen(subgen=(pausegen, pausegen, mksingen(3)),
                mode=GradPosition.REPEAT,
                name='ch2seq')

    wavegen = ParallelGenGradGen(subgen=(ch0gen, ch1gen, ch2gen), name='par1-3')

    noisegen = EnvelopeGenGradGen(sourcegen=NoiseGen(minValues=(0.3, 0.3, 0.3), maxValues=(1.0, 1.0, 1.0),
                                                name='noise'),
                                  envelopegen=LineGradGen(length=8.0, channelsFrom=(1.0,), channelsTo=(0.0,),
                                                name='noisefade'),
                                  name='envnoise')

    maingen = CrossfadeGenGradGen(source1gen=noisegen,
                                  source2gen=wavegen,
                                  balancegen=LineGradGen(length=12.0,
                                        channelsFrom=(0.0,),
                                        channelsTo=(1.0,),
                                        name='mainbalance'),
                                  name='crossfade')

    return maingen


def choose_demonstration():
    demos = (('LineGradGen', demo_LineGradGen),
             ('SineWaveGradGen', demo_SineWaveGradGen),
             ('SquareWaveGradGen', demo_SquareWaveGradGen),
             ('EnvelopeGenGradGen', demo_EnvelopeGenGradGen),
             ('NoiseGen', demo_NoiseGen),
             ('ImageGradGen', demo_ImageGradGen),
             ('SequenceGenGradGen', demo_SequenceGenGradGen),
             ('CrossfadeGenGradGen', demo_CrossfadeGenGradGen),
             )

    print('DMXGRAD r%s demonstration:' % REVISION)

    dfunction = None
    for ix, (dname, _) in enumerate(demos, 1):
        print('%d. %s' % (ix, dname))

    dnum = int(input('Enter demonstration number, then press RETURN: '))

    if dnum >=1 and dnum <= len(demos):
        dfunc = demos[dnum - 1][1]
        print(dfunc.__name__)
        return dfunc()


def main():
    class MySender(GradSender):
        def display(self, values, gen):
            print('%4s: %s  %s' % ('∞' if self.iterations is None else self.iterations,
                  channels_to_str(values, 8),
                  gen.get_disp_name()))

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
