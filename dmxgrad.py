#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" dmxgrad.py

    Кривой прототип кривого костыля для кормления DMX512-совместимых
    устройств байтами из выхлопа скриптов на питоне.

    Внимание! Это поделие создано для баловства, и категорически
    НЕ предназначено для управления взаправдашним сценическим
    оборудованием на взаправдашней сцене.

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


REVISION = 3


from math import sin, pi
from random import randint

# для генераторов, берущих данные из загружаемых изображений
# требуется PIL или PILLOW!
from PIL import Image

import array
from ola.ClientWrapper import ClientWrapper


def unwrap_values(l):
    """Рекурсивное разворачивание списка списков (и/или кортежей)
    целых чисел в один список.

    Предназначено для преобразования значений, возвращаемых методом
    *GradGen.next_position() в вид, пригодный для передачи устройству
    DMX-512."""

    if isinstance(l, int):
        return [l]

    ret = []

    for v in l:
        if isinstance(v, list) or isinstance(v, tuple):
            ret += unwrap_values(v)
        else:
            ret.append(v)

    return ret


def repr_to_str(obj, sli=False):
    """Форматирование строки с именем класса и значениями полей экземпляра
    класса для использования в методах obj.__repr__().
    Внимание! Если классы, использующие эту функцию, содержат в полях
    ссылки друг на друга, возможно зацикливание.
    В данной версии функции предотвращение зацикливания пока не реализовано.

    Параметры:
        obj - экземпляр произвольного класса;
        sli - булевское значение, управляющее отображением списков
              и кортежей:
              False - отображать только количество элементов,
              True  - отображать весь список (кортеж).

    Функция возвращает строку."""

    r = []

    def __repr_item(i):
        if isinstance(i, str):
            return i

        try:
            iter(i)
            return '[%d item(s)]' % len(i)
        except TypeError:
            return str(i)

        return i

    def __repr_dict(dname):
        d = getattr(obj, dname, None)
        if d:
            for k, v in d.items():
                r.append('%s=%s' % (k, __repr_item(v)))

    __repr_dict('__dict__')
    __repr_dict('__slots__')

    return '%s(%s)' % (obj.__class__.__name__,
        ', '.join(r))


class GradPosition():
    """Счетчик положения для выборки значений.

    Поля:
        value       - положительное целое, текущее положение;
        length      - положительное целое, >= 1 - количество значений;
        direction   - целое, -1 или 1, приращение положения;
        mode        - целое, управляет поведением при достижении
                      крайних значений (см. ниже).

    Поведение при достижении крайних значений:
        STOP    - изменение value прекращается;
        REPEAT  - генерация продолжается с начала (value=0);
        MIRROR  - инвертируется знак direction, генерация идёт
                  "задом наперёд" до достижения value==0, и т.д.;
        RANDOM  - возвращает случайное значение 0 <= N < length."""

    STOP, REPEAT, MIRROR, RANDOM = range(4)

    def __init__(self, length=1, mode=STOP, direction=1):
        """Инициализация счётчика.

        Параметры:
            length - положительное целое >0, количество значений;
            mode, direction - см. описание соотв. полей класса."""

        self.set_length(length)

        if direction in (-1, 1):
            self.direction = direction
        else:
            raise ValueError('%s.__init__(): invalid "direction" value (must be 1 or -1)' % self.__class__.__name__)

        self.mode = mode

        self.begin()

    def __repr__(self):
        return repr_to_str(self)

    def set_length(self, l):
        """Установка количества значений.

        nv      - положительное целое (количество значений) или кортеж/список/...,
                  длину которого следует использовать."""

        if not isinstance(l, int):
            try:
                l = len(l)
            except:
                raise ValueError('%s.set_length(): invalid type of "length" parameter' % self.__class__.__name__)

        if l < 0:
            raise ValueError('%s.set_length(): length must be positive integer' % self.__class__.__name__)

        self.length = l
        self.begin()

    def begin(self):
        """Установка полей в начальные значения"""

        self.value = 0
        self.direction = 1

    def end(self, back=False):
        """Установка полей в конечные значения"""

        self.value = self.length - 1
        self.direction = 1 if not back else -1

    def next_value(self):
        """Изменение значения поля value в соответствии со значениями
        полей mode и direction.
        Возвращает полученное значение value."""

        if self.length < 2:
            return 0

        _lv = self.length - 1

        if self.mode == self.STOP:
            if self.value < _lv:
                self.value += self.direction
        elif self.mode == self.REPEAT:
            self.value = (self.value + self.direction) % self.length
        elif self.mode == self.MIRROR:
            self.value += self.direction

            if self.value > _lv:
                self.value = _lv - 1
                self.direction = - self.direction
            elif self.value < 0:
                self.value = 1
                self.direction = - self.direction
        else: #RANDOM
            self.value = randint(0, _lv)

        return self.value


class GradGen():
    """Базовый класс генератора градиентов.
    Протоколы итераторов и генераторов НЕ используются, так как
    эти классы могут (и имеют право) выдавать бесконечные последовательности,
    из-за чего код, использующий "питоньи" итераторы и генераторы
    обычным образом, мог бы зациклиться.

    Поля класса (могут быть перекрыты и/или дополнены классом-потомком):
        DEFAULT_MODE - значение, которое будет использовано
                      счётчиком положения, если ему не передавать соотв.
                      параметр; по умолчанию - GradPosition.STOP;
        MAX_VALUE   - максимальное возвращаемое значение.

    Поля экземпляров класса (могут быть дополнены классом-потомком):
        position    - экземпляр GradPosition."""

    DEFAULT_MODE = GradPosition.STOP
    MAX_VALUE = 255

    def __init__(self, **kwargs):
        """Параметры: см. список полей экземпляра класса.

        Этот конструктор и конструкторы классов-потомков получают
        параметры в виде словаря kwargs вместо прямого перечисления
        параметров, дабы не заморачиваться при наследовании
        и вызовах super().
        Названия передаваемых параметров должны соответствовать
        названиям полей экземпляра соотв. класса."""

        self.position = GradPosition(kwargs.get('length', 1),
            kwargs.get('mode', self.DEFAULT_MODE))

        self.reset()

    def reset(self):
        """Сброс полей в начальные значения и расчёт значений, которые
        не требуется считать "на лету".
        Метод может быть перекрыт классом-потомком, вызов метода reset()
        предка потомками обязателен, если они не сбрасывают все поля
        сами."""

        self.position.begin()

    def __repr__(self):
        return repr_to_str(self)

    def get_n_values(self):
        """Метод возвращает максимальное количество возвращаемых значений.
        Обычно оно равно position.length, но особо заковыристые генераторы
        могут возвращать другие значения (см. реализацию метода
        в конкретном классе)."""

        return self.position.length

    def get_next_value(self):
        """Метод возвращает очередное значение градиента в виде целого
        числа в диапазоне 0..255 или списка/кортежа таких целых,
        и увеличивает при необходимости счётчик.
        Метод должен быть перекрыт классом-потомком."""

        raise NotImplementedError()

        #self.position.next_value()


class BufferedGradGen(GradGen):
    """Генератор, хранящий заранее расчитанные значения в буфере.

    Поля (могут быть дополнены классом-потомком):
        buffer      - список целых (или списков/кортежей целых чисел)
                      в диапазоне 0..255, из которого ведётся выборка
                      сгенерированных значений;
        clearBuf    - булевское значение; если равно True (по умолчанию) -
                    buffer очищается при вызове метода reset()."""

    def __init__(self, **kwargs):
        self.clearBuf = kwargs.get('clearBuf', True)
        self.buffer = []
        super().__init__(**kwargs)

        d = kwargs.get('data', None)
        if d:
            self.set_buffer_data(d)

    def reset(self):
        """Заполнение списка buffer сгенерированными значениями,
        в дополнение к дейстивиям метода GradGen.reset()."""

        super().reset()

        if self.clearBuf:
            self.buffer.clear()

    def set_buffer_data(self, d):
        self.buffer = list(d)
        self.position.set_length(self.buffer)

    def get_next_value(self):
        ret = self.buffer[self.position.value]

        self.position.next_value()

        return ret


class SineGradGen(BufferedGradGen):
    """Генератор синусоиды.

    Генерирует синусоиду с длиной периода в length значений."""

    def reset(self):
        super().reset()

        sinCf = 2 * pi / self.position.length
        sinOffset = pi / 2
        middle = self.MAX_VALUE / 2.0

        for i in range(self.position.length):
            self.buffer.append(int(middle - middle * sin(sinOffset + i * sinCf)))


class LineGradGen(BufferedGradGen):
    """Генератор линейного градиента.
    Может быть использован для генерации пилообразных (с mode=GradPosition.REPEAT)
    и треугольных волн (mode=GradPosition.MIRROR).

    Параметры:
        fadeout - булевское значение;
                  при fadeout==True генерируются значения от максимального
                  к минимальному,
                  при fadeout==False (по умолчанию) - от минимального
                  к максимальному."""

    def __init__(self, **kwargs):
        self.fadeout = kwargs.get('fadeout', False)

        super().__init__(**kwargs)

    def reset(self):
        super().reset()

        dy = self.MAX_VALUE / (self.position.length - 1)

        if self.fadeout:
            v = self.MAX_VALUE
            dy = -dy
        else:
            v = 0.0

        for i in range(self.position.length):
            self.buffer.append(int(v))
            v += dy


class ImageGradGen(BufferedGradGen):
    """Возвращает данные из растрового изображения.

    Поля экземпляра класса (в дополнение к полям GradGen):
        image       - экземпляр PIL.Image;
        horizontal  - булевское значение или None (по умолчанию)
                      True  - генератор получает данные из строки
                              изображения,
                      False - из столбца,
                      None  - автоматическое определение по пропорциям
                              изображения;
        srcx, srcy  - начальные координаты строки или столбца в изображении;
                      по умолчанию - 0, 0;
        channels    - кортеж целых чисел, каналы изображения
                      (0 - R, 1 - G и т.п.).

    Для получения нескольких каналов изображения есть два варианта действий:
    1. создать один ImageGradGen с указанием нескольких каналов;
    2. создать соответствующее количество экземпляров ImageGradGen с указанием
       каналов и эти экземпляры добавить в экземпляр ParallelGenGradGen;
       в этом случае можно использовать каналы из разных изображений."""

    def __init__(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        self.image = kwargs.get('image', None)
        if not self.image:
            raise ValueError('%s.__init__(): "image" parameter not specified' % self.__class__.__name__)

        self.horizontal = kwargs.get('horizontal', None)
        if self.horizontal is None:
            self.horizontal = self.image.width > self.image.height

        #TODO возможно, следует добавить проверку на правильность значений номеров каналов
        self.channels = tuple(set(kwargs.get('channels', (0,))))

        self.srcx = kwargs.get('srcx', 0)
        self.srcy = kwargs.get('srcy', 0)

        super().__init__(**kwargs)

    def reset(self):
        # проверяем выход за границы именно здесь, т.к. length/srcx/srcy
        # могут быть изменены уже после создания экземпляра класса

        __E_OUT_OF_IMAGE = 'gradient goes beyond the boundaries of the image'

        if self.horizontal:
            self.position.length = self.image.width

            if (self.srcx + self.position.length) > self.image.width:
                raise IndexError(__E_OUT_OF_IMAGE)

            dx = 1
            dy = 0
        else:
            self.length = self.image.height

            if (self.srcy + self.position.length) > self.image.height:
                raise IndexError(__E_OUT_OF_IMAGE)

            dx = 0
            dy = 1

        super().reset()

        x = self.srcx
        y = self.srcy
        for i in range(self.position.length):
            pixel = self.image.getpixel((x, y))
            self.buffer.append(tuple(map(lambda c: pixel[c], self.channels)))

            x += dx
            y += dy


class ConstantGradGen(GradGen):
    """Псевдо-генератор, выдающий лишь одно значение.

    Поля экземпляра класса:
        value   - целое, 0..255 - возвращаемое значение.

    Счетчик положения не используется."""

    def __init__(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        super().__init__(**kwargs)

        self.value = kwargs.get('value', 0)

    def get_next_value(self):
        return self.value


class SquareGradGen(BufferedGradGen):
    """Генератор меандра.

    Генерирует меандр с длиной периода в length/2 значений.

    Поля класса:
        LOW_VALUE   - целое, 0..255, значение "нуля" меандра по умолчанию;
        HIGH_VALUE  - целое, 0..255, значение "единицы" меандра по умолчанию.

    Поля экземпляра класса (в дополнение к унаследованным):
        lowv    - целое, 0..255, значение "нуля" меандра;
        highv   - целое, 0..255, значение "единицы" меандра."""

    DEFAULT_MODE = GradPosition.REPEAT

    LOW_VALUE = 0
    HIGH_VALUE = BufferedGradGen.MAX_VALUE

    #TODO присобачить реализацию длительностей импульса и паузы

    def __init__(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        self.lowv = kwargs.get('lowv', self.LOW_VALUE)
        self.highv = kwargs.get('highv', self.HIGH_VALUE)

        super().__init__(**kwargs)

    def reset(self):
        super().reset()

        half = self.position.length // 2
        # а кто указал нечётное значение length конструктору - сам себе оно самое

        self.buffer += [self.lowv] * half
        self.buffer += [self.highv] * half


class GenGradGen(GradGen):
    """Генератор, возвращающий значения от вложенных генераторов.

    Внимание! Поля экземпляра класса GenGradGen (position и т.п.)
    могут не использоваться классами-потомками.
    После последнего вызова add_subgen() следует вызвать метод reset()."""

    def __init__(self, **kwargs):
        self.generators = []
        super().__init__(**kwargs)

    def add_subgen(self, *gen):
        """Добавление одного или нескольких вложенных генераторов.

        gen - экземпляр(ы) класса GradGen."""

        self.generators += gen

        self.position.set_length(self.generators)

    def reset(self):
        self.position.set_length(self.generators)

        super().reset()

        for g in self.generators:
            g.reset()


class ParallelGenGradGen(GenGradGen):
    """Генератор, возвращающий сгруппированные значения
    от всех вложенных генераторов."""

    def get_n_values(self):
        m = 0
        for g in self.generators:
            v = g.get_n_values()
            if v > m:
                m = v

        return m

    def get_next_value(self):
        return [g.get_next_value() for g in self.generators]


class SequenceGenGradGen(GenGradGen):
    """Генератор, вызывающий вложенные генераторы поочерёдно.
    Количество последовательных вызовов каждого генератора
    соответствует значению соотв. position.length.
    По окончании списка генераторов перебор начинается сначала."""

    def __init__(self, **kwargs):
        self.activeGen = None
        self.activeItrs = 0

        super().__init__(**kwargs)

    def __set_active_gen(self):
        if self.generators:
            self.activeGen = self.generators[self.position.value]
            self.activeItrs = self.activeGen.get_n_values()
            #print(f'{self.activeGen=}, {self.activeItrs=}')
        else:
            self.activeGen = None
            self.activeItrs = 0

    def reset(self):
        super().reset()
        self.__set_active_gen()

    def get_n_values(self):
        r = 0

        for g in self.generators:
            r += g.get_n_values()

        return r

    def get_next_value(self):
        if not self.activeGen:
            raise ValueError('generator not properly initialized')

        ret = self.activeGen.get_next_value()

        if self.activeItrs:
            self.activeItrs -= 1
        else:
            self.position.next_value()
            self.__set_active_gen()

        return ret


class GradSender():
    DEFAULT_TICK_INTERVAL = 100  # в миллисекундах

    """Обёртка над обёрткой для кормления DMX512-совместимых устройств
    байтами, выданными генераторами градиентов.

    Поля:
        generator   - экземпляр класса GradGen;
        universe    - номер DMX-512 universe;
        iterations  - None или положительное целое: количество значений,
                      которые будут сгенерированы при вызове метода run();
                      если iterations is None - метод run() будет
                      работать бесконечно (или пока его не прервут
                      установкой поля stop в True или вместе со скриптом);
        interval    - целое, интервал в миллисекундах между отправками
                      значений устройствам;
        stop        - булевское значение, флаг прекращения работы цикла
                      в методе run()."""

    def __init__(self, uv, gen, itrs, ms=DEFAULT_TICK_INTERVAL):
        self.wrapper = ClientWrapper()

        self.generator = gen
        self.universe = uv
        self.iterations = itrs
        self.interval = ms
        self.lastState = None

        self.stop = False

    def __repr__(self):
        return repr_to_str(self)

    def __DMX_sent(self, state):
        self.lastState = state

        if not state.Succeeded():
            self.wrapper.Stop()

    def __DMX_send_frame(self):
        if self.stop:
            self.wrapper.Stop()
            return

        if self.iterations is not None:
            self.iterations -= 1
            if self.iterations <= 0:
                self.wrapper.Stop()
                return

        self.wrapper.AddEvent(self.interval, self.__DMX_send_frame)

        values = unwrap_values(self.generator.next_position())
        self.display(values)
        data = array.array('B', values)

        self.wrapper.Client().SendDmx(self.universe, data, self.__DMX_sent)

    def display(self, values):
        """При необходимости отображения текущих значений и прочей
        информации этот метод должен быть перекрыт классом-потомком."""

        #print('sending: %s, iteration(s) left: %d' % (data, self.iterations))
        pass

    def run(self):
        self.stop = False
        self.wrapper.AddEvent(self.interval, self.__DMX_send_frame)
        self.wrapper.Run()


def __debug_GradGen():
    import signal

    img = Image.open('gradient2.png')

    # 1
    """rgb = ParallelGenGradGen(mode=GradPosition.REPEAT)
    for c in range(3):
        rgb.add_subgen(ImageGradGen(image=img, channels=c, mode=GradPosition.REPEAT))"""
    # 2
    rgb = ImageGradGen(image=img, channels=(0,1,2), mode=GradPosition.REPEAT)

    #allgen = ParallelGenGradGen()
    allgen = SequenceGenGradGen(mode=GradPosition.REPEAT)

    allgen.add_subgen(rgb)
    allgen.add_subgen(LineGradGen(length=35, mode=GradPosition.MIRROR))
    allgen.add_subgen(SineGradGen(length=16, mode=GradPosition.REPEAT))
    allgen.add_subgen(ConstantGradGen(value=1))
    allgen.add_subgen(SquareGradGen(length=16, lowv=0, highv=GradGen.MAX_VALUE))
    allgen.add_subgen(BufferedGradGen(clearBuf=False, mode=GradPosition.REPEAT, data=(0, 128, 255)))
    allgen.reset()

    print('Press Ctrl+C to stop')

    allgen.stop = False

    def __sigint_handler(sig, frame):
        allgen.stop = True

    oldCC = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, __sigint_handler)

    i = 1
    while not allgen.stop:
        v = ', '.join(map(lambda n: '%.2x' % n, unwrap_values(allgen.get_next_value())))

        #print('\r%8d  %s\033[K' % (i, v), end='')
        print('%8d  %s' % (i, v))
        i += 1

    signal.signal(signal.SIGINT, oldCC)
    print('\n***END***')


def __debug_GradPosition():
    for mode in (GradPosition.STOP, GradPosition.REPEAT, GradPosition.MIRROR):
        pos = GradPosition(6, mode)

        print(f'{mode=}')

        for i in range(pos.length * 2):
            print('%2d  %d' % (i, pos.value))
            pos.next_value()

def __debug_random():
    allgen = SequenceGenGradGen(mode=GradPosition.RANDOM)

    allgen.add_subgen(LineGradGen(length=5, mode=GradPosition.MIRROR),
        SineGradGen(length=6, mode=GradPosition.REPEAT),
        ConstantGradGen(value=111),
        SquareGradGen(length=6, lowv=0, highv=GradGen.MAX_VALUE),
        BufferedGradGen(clearBuf=False, mode=GradPosition.REPEAT,
            data=((0, 0, 0),(128, 128, 128), (255, 255, 255))))
    allgen.reset()

    n = allgen.get_n_values()
    while n > 0:
        n -= 1

        print(unwrap_values(allgen.get_next_value()))


if __name__ == '__main__':
    print('[debugging %s]' % __file__)

    #__debug_GradPosition()
    #__debug_GradGen()
    __debug_random()

