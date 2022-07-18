#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" dmxgrad.py

    Кривой прототип кривого костыля для кормления DMX512-совместимых
    устройств байтами из выхлопа скриптов на питоне.

    Внимание!
    1. Это поделие создано для баловства, и категорически НЕ предназначено
       для управления взаправдашним сценическим оборудованием на взаправдашней
       сцене.
    2. Потроха поделия могут быть в любой момент изменены до полной
       неузнаваемости и несовместимости с предыдущей версией.

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


REVISION = 12


from math import sin, pi
from random import randint, random

# для генераторов, берущих данные из загружаемых изображений
# требуется PIL или PILLOW!
from PIL import Image

from array import array
from ola.ClientWrapper import ClientWrapper

from colorsys import hls_to_rgb


# значения цветов для функции hls_to_rgb()
__HUE_360 = 1.0 / 360

HUE_RED     = 0.0
HUE_ORANGE  = 30 * __HUE_360
HUE_YELLOW  = 60 * __HUE_360
HUE_GREEN   = 120 * __HUE_360
HUE_CYAN    = 180 * __HUE_360
HUE_BLUE    = 240 * __HUE_360
HUE_MAGENTA = 300 * __HUE_360


MAX_VALUE = 1.0

# готовые значения цветов (R, G, B)
RGB_RED     = (MAX_VALUE, 0, 0)
__MAX_LIGHTNESS = 0.5 # максимальное значение яркости в HLS, при котором цвет не пересвечивается в белый
RGB_ORANGE  = hls_to_rgb(HUE_ORANGE, __MAX_LIGHTNESS, 1)
RGB_YELLOW  = hls_to_rgb(HUE_YELLOW, __MAX_LIGHTNESS, 1)
RGB_GREEN   = hls_to_rgb(HUE_GREEN, __MAX_LIGHTNESS, 1)
RGB_CYAN    = hls_to_rgb(HUE_CYAN, __MAX_LIGHTNESS, 1)
RGB_BLUE    = hls_to_rgb(HUE_BLUE, __MAX_LIGHTNESS, 1)
RGB_MAGENTA = hls_to_rgb(HUE_MAGENTA, __MAX_LIGHTNESS, 1)


def str_to_rgb(s):
    """Преобразование значения цвета из строки вида "#RRGGBB", "#RGB",
    "RRGGBB" или "RGB" в кортеж из трёх целых в диапазоне 0..MAX_VALUE."""

    __E_RGB = 'str_to_rgb(s): invalid format of "s" parameter'

    sl = len(s)
    if sl not in (3, 4, 6, 7):
        raise ValueError(__E_RGB)

    if sl in (4, 7):
        if s[0] != '#':
            raise ValueError(__E_RGB)
        so = 1
    else:
        so = 0

    pl = 1 if sl in (3, 4) else 2

    ret = []
    for ix in range(3):
        six = so + ix * pl
        ret.append(int(s[six:six + pl], 16))

    return tuple(ret)


def get_supported_image(fromimg, grayscale=False):
    """Проверяет формат изображения, при необходимости создаёт
    новый экземпляр в совместимом с этим модулем формате - L или RGB(A).

    Параметры:
        fromimg     - экземпляр класса изображения, созданный с помощью
                      Image.open;
        grayscale   - булевское значение; если True - исходное изображение
                      конвертируется в шкалу серого, иначе - в RGB.

    Возвращает новое изображение в совместимом формате, если формат
    исходного изображения несовместим, иначе возвращает значение fromimg."""

    destmode = 'L' if grayscale else 'RGB'

    if fromimg.mode == destmode:
        return fromimg

    ret = Image.new('RGB', fromimg.size)
    ret.paste(fromimg)

    return ret


def unwrap_lol(sl):
    """Рекурсивное разворачивание списка списков (и/или кортежей)
    чисел в один список. Возвращает линейный список.
    Может использоваться генераторами, получающими значения от других
    генераторов (например, от ParallelGenGradGen)."""

    if isinstance(sl, int):
        return [sl]

    dl = []

    for v in sl:
        if isinstance(v, list) or isinstance(v, tuple):
            dl += unwrap_lol(v)
        else:
            dl.append(v)

    return dl


def channels_to_str(channels):
    """Пребразование списка/кортежа, содержащего значения float
    в диапазоне 0.0-1.0 (и/или кортежи с такими значениями) в строку
    с горизонтальными диаграммами и численными значениями (в виде
    шестнадцатиричных чисел в диапазоне 0x00-0xFF).
    Функция предназначена для визуализации при отладке генераторов."""

    #__BCHARS = '▏▎▍▌▋▊▉'
    __BCHARS = '░▒▓█'
    __BCCOUNT = len(__BCHARS)

    def __val_disp(v):
        blen = int(v * __BCCOUNT)
        if blen >= __BCCOUNT:
            # значение 1.0 при преобразовании приведет к выходу за
            # границу списка, заодно подстрахуемся от кривых значений
            # > 1.0
            blen = __BCCOUNT - 1

        return '%s %.2x' % (__BCHARS[blen], int(v * 255))

    return '|'.join(map(__val_disp, unwrap_lol(channels)))


def check_float_range_1(f):
    """Проверка float значения на попадание в диапазон 0.0-1.0.
    В случае несоответствия генерируется исключение.
    Функция предназначена для использования в конструкторах классов."""

    if f < 0.0 or f > 1.0:
        raise ValueError('value out of range')


def check_float_positive(f):
    """Проверка float значения на допустимое значение (положительное число).
    В случае несоответствия генерируется исключение.
    Функция предназначена для использования в конструкторах классов."""

    if f > 0.0:
        return

    raise ValueError('value out of range')



def fparam_to_tuple(args, pname, fallback, tolength=None, chkval=None):
    """Получение и нормализация параметра.

    Метод предназначен для обработки параметров конструкторов классов.

    Параметры:
        args        - словарь с параметрами (kwargs конструктора);
        pname       - строка, имя параметра;
        fallback    - кортеж из float, значение параметра по умолчанию;
        tolength    - None или положительное целое;
                      если указано положительное целое - кортеж
                      расширяется до указаной длины с использованием
                      значений fallback, повторяемых циклически;
        chkval      - None или функция, получающая значение,
                      и генерирующая исключение, если значение недопустимое.
    Возвращает кортеж из float."""

    pval = args.get(pname, fallback)

    if isinstance(pval, (list, tuple)):
        if len(pval) < 1:
            raise ValueError('"%s" parameter must contain at least one float value' % pname)

        pval = list(pval)
    else:
        pval = [pval]

    if not callable(chkval):
        chkval = lambda v: v

    for ix, v in enumerate(pval):
        try:
            # принудительно преобразуем значения во float
            pval[ix] = float(v)
            # и проверяем само значение
            chkval(v)
        except Exception as ex:
            raise ValueError('value #%d of parameter "%s" is invalid - %s' % (ix + 1, pname, str(ex)))

    pvlen = len(pval)
    fblen = len(fallback)

    if (tolength is not None) and tolength > 1 and pvlen < tolength:
        pval += [fallback[ix % fblen] for ix in range(tolength - pvlen)]

    return tuple(pval)


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
        ncycles     - количество полных циклов счётчика - увеличивается
                      на 1 по достижении крайних значений;
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

        self.ncycles = 0

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

    @staticmethod
    def compute_length(seconds, sendint):
        """Расчёт количества шагов градиента на основе
        длительности в секундах и интервала между обращениями
        к устройству DMX512.

        Параметры:
            seconds - int или float, длительность в секундах;
            sendint - int или float, количество обращений к устройству в секунду.

        Возвращает целое число."""

        return int(1000 * seconds / sendint)

    def set_length_from_time(self, seconds, sendint):
        """Установка поля length на основе длительности.
        См. также метод compute_length()."""

        self.set_length(self.compute_length(seconds, sendint))

    def begin(self):
        """Установка полей в начальные значения"""

        self.value = 0
        self.direction = 1
        self.ncycles += 1

    def end(self, back=False):
        """Установка полей в конечные значения"""

        self.value = self.length - 1
        self.direction = 1 if not back else -1
        self.ncycles += 1

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
                self.ncycles += 1
        elif self.mode == self.REPEAT:
            self.value = self.value + self.direction
            if self.value < 0 or self.value == self.length:
                self.ncycles += 1
                self.value %= self.length
        elif self.mode == self.MIRROR:
            self.value += self.direction

            if self.value > _lv:
                self.value = _lv - 1
                self.direction = - self.direction
                self.ncycles += 1
            elif self.value < 0:
                self.value = 1
                self.direction = - self.direction
                self.ncycles += 1
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
                      параметр; по умолчанию - GradPosition.STOP.

    Поля экземпляров класса (могут быть дополнены классом-потомком):
        position    - экземпляр GradPosition;
        name        - отображаемое имя (для отладки и т.п.);
                      если не указано при вызове конструктора -
                      генерируется автоматически."""

    DEFAULT_MODE = GradPosition.STOP

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

        self.name = kwargs.get('name', '%s%x' % (self.__class__.__name__, id(self)))

        self.reset()

    def get_disp_name(self):
        """Возвращает строку с отображаемым именем экземпляра класса.
        В простейшем случае это значение поля name, а генераторы,
        содержащие другие генераторы, должны добавлять их имена
        в возвращаемое значение."""

        return self.name

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
        """Метод возвращает очередное значение градиента в виде float
        0.0-1.0 или списка/кортежа таких значений,
        и увеличивает при необходимости счётчик.
        Метод должен быть перекрыт классом-потомком."""

        raise NotImplementedError()

        #self.position.next_value()


class BufferedGradGen(GradGen):
    """Генератор, хранящий заранее расчитанные значения в буфере.

    Поля (могут быть дополнены классом-потомком):
        buffer      - список float (или списков/кортежей float)
                      в диапазоне 0.0-1.0, из которого ведётся выборка
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


class LineGradGen(BufferedGradGen):
    """Генератор линейного градиента.
    Может быть использован для генерации пилообразных (с mode=GradPosition.REPEAT)
    и треугольных волн (mode=GradPosition.MIRROR).

    Поля:
        channelsFrom, channelsTo  - кортежи из одного и более float
            в диапазоне 0.0-1.0;
            количество значений в обоих кортежах может совпадать.
        Количество значений в переходе управляется полем position.length."""

    def __init__(self, **kwargs):
        """Параметры (в дополнение к "наследственным"):
            channelsFrom, channelsTo (см. описания одноимённых полей);
                их значения могут быть указаны в виде кортежей или преобразованы
                из значений цветов вызовами hls_to_rgb(), str_to_rgb()."""

        def __channels(parName, defv, cklen):
            c = kwargs.get(parName, defv)

            __ERR = '%s.__init__(): parameter "%s" is invalid - %%s' % (self.__class__.__name__, parName)

            if not isinstance(c, tuple):
                raise ValueError(__ERR % 'invalid type')

            if cklen is not None and len(c) != cklen:
                raise ValueError(__ERR % 'invalid length')

            for ix, v in enumerate(c, 1):
                if not isinstance(v, int):
                    raise ValueError(__ERR % 'invalid type of element #%d' % ix)

                if v < 0 or v > MAX_VALUE:
                    raise ValueError(__ERR % 'element #%d out of range' % ix)

            return c

        self.channelsFrom = __channels('channelsFrom', (0,), None)
        self.channelsTo = __channels('channelsTo', (MAX_VALUE,), len(self.channelsFrom))

        super().__init__(**kwargs)

    def reset(self):
        super().reset()

        _len = self.position.length - 1
        _chans = len(self.channelsFrom)

        deltas = []
        cvals = []

        for c in range(_chans):
            deltas.append((self.channelsTo[c] - self.channelsFrom[c]) / _len)
            cvals.append(self.channelsFrom[c])

        for i in range(self.position.length):
            self.buffer.append(tuple(map(int, cvals)))

            for c in range(_chans):
                cvals[c] += deltas[c]


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
        """Параметры: см. описание полей экземпляра класса.
        """

        self.image = kwargs.get('image', None)
        if not self.image:
            raise ValueError('"image" parameter not specified')

        if self.image.mode not in ('L', 'RGB', 'RGBA'):
            raise ValueError('unsupported image format')

        srcchnls = kwargs.get('channels', None)
        if srcchnls is None:
            if self.image.mode == 'L':
                self.channels = (0,)
            else:
                # 'RGB', 'RGBA'
                # если нужно использовать и альфа-канал - следует указывать каналы в параметре явно
                self.channels = (0, 1, 2)
        else:
            #TODO возможно, следует добавить проверку на правильность значений номеров каналов в параметре channels
            if len(srcchnls) > len(self.image.mode): #!!!!
                raise ValueError('too many channel numbers specified')

            self.channels = tuple(srcchnls)

        self.horizontal = kwargs.get('horizontal', None)
        if self.horizontal is None:
            self.horizontal = self.image.width > self.image.height

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
            self.position.length = self.image.height

            if (self.srcy + self.position.length) > self.image.height:
                raise IndexError(__E_OUT_OF_IMAGE)

            dx = 0
            dy = 1

        super().reset()

        x = self.srcx
        y = self.srcy
        for i in range(self.position.length):
            pixel = self.image.getpixel((x, y))
            self.buffer.append(tuple(map(lambda c: pixel[c] / 255.0, self.channels)))

            x += dx
            y += dy


class ConstantGradGen(GradGen):
    """Псевдо-генератор, выдающий постоянные значения.

    Поля экземпляра класса:
        values   - кортеж из float в диапазоне 0.0-1.0.

    Счетчик положения не используется."""

    def __init__(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        super().__init__(**kwargs)

        self.values = fparam_to_tuple(kwargs, 'value', (0, ))

    def get_next_value(self):
        return self.values


class NoiseGen(GradGen):
    """Генератор шума.

    Поля экземпляра класса:
        minValues, maxValues
            - кортежи из float в диапазоне 0.0-1.0 с граничными значениями
              для каналов.

    Счетчик положения не используется."""

    def __init__(self, **kwargs):
        self.minValues = fparam_to_tuple(kwargs, 'minValues', (0.0, ),
                            None, check_float_range_1)
        self.maxValues = fparam_to_tuple(kwargs, 'maxValues', (1.0, ),
                            len(self.minValues), check_float_range_1)

        super().__init__(**kwargs)

    def reset(self):
        pass

    def get_next_value(self):
        ranges = [(self.maxValues[i] - minv) for i, minv in enumerate(self.minValues)]

        ret = []

        for ci, minv in enumerate(self.minValues):
            ret.append(minv + random() * ranges[ci])

        return ret


class WaveGradGen(BufferedGradGen):
    """Базовый класс для генераторов волн.

    Поле position.length задаёт количество значений в буфере.
    Дополнительные поля (в дополнение к наследственным):
        levels  - кортеж из одного и более float в диапазоне от 0 до 1.0 -
                  максимальные значения уровней каналов;
                  по умолчанию - (1.0, );
                  количество каналов генератора задаётся этим параметром;
        lowLevels - минимальные значения уровней каналов (аналогично
                  полю levels);
        periods - кортеж из одного и более положительных float,
                  задаёт количество периодов волны для одного
                  или нескольких каналов;
                  если указано меньше значений, чем количество каналов -
                  значения периодов повторяются циклически "до заполнения";
        phases  - кортеж из одного и более float в диапазоне от 0 до 1.0 -
                  значения фазы волны для генерируемых значений каналов;
                  по умолчанию - (0.0, )
                  если указано меньше значений, чем количество каналов -
                  значения периодов повторяются циклически "до заполнения"."""

    def __init__(self, **kwargs):
        """Параметры (в дополнение к наследуемым):
            levels, phases, periods (см. описание полей выше);
            Примечание: вместо кортежей этим параметрам можно присваивать
            по одному значению float, в этом случае параметр будет
            преобразован в кортеж из одного элемента."""

        self.levels = fparam_to_tuple(kwargs, 'levels', (1.0, ), None, check_float_range_1)
        _ll = len(self.levels)

        self.lowLevels = fparam_to_tuple(kwargs, 'lowLevels', (0.0, ), _ll, check_float_range_1)

        self.phases = fparam_to_tuple(kwargs, 'phases', (0.0, ), _ll, check_float_range_1)

        self.periods = fparam_to_tuple(kwargs, 'periods', (1.0, ), _ll, check_float_positive)

        super().__init__(**kwargs)


class SineWaveGradGen(WaveGradGen):
    """Генератор синусоиды."""

    def reset(self):
        super().reset()

        periodCf = [(self.position.length / period) for period in self.periods]
        phaseCf = [(periodCf[ci] * self.phases[ci]) for ci in range(len(self.levels))]

        sinCf = [(2 * pi / pp) for pp in periodCf]
        sinOffset = pi / 2 # дабы синусоида завсегда начиналась с минимального значения

        #FIXME исправить генерацию синусоиды с учётом lowLevels

        for i in range(self.position.length):
            v = []

            for ci, level in enumerate(self.levels):
                middle = level / 2.0
                v.append(middle - middle * sin(sinOffset + (i + phaseCf[ci]) * sinCf[ci]))

            self.buffer.append(v)


class SquareWaveGradGen(WaveGradGen):
    """Генератор меандра.

    Поля экземпляра класса (в дополнение к унаследованным):
        dutyCycles  - коэффициенты заполнения для каналов;
                      по умолчанию - 1.0."""

    def __init__(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        __DEF_DC = 1.0

        self.dutyCycles = fparam_to_tuple(kwargs, 'dutyCycles', (__DEF_DC, ), None, check_float_range_1)

        super().__init__(**kwargs)

        # костылинг, т.к. на момент присвоения значения dutyCycles
        # количество каналов ещё не было известно
        ldc = len(self.dutyCycles)
        nchns = len(self.levels)
        if ldc < nchns:
            self.dutyCycles += [__DEF_DC] * (nchns - ldc)

    def reset(self):
        super().reset()

        periodCf = [(self.position.length / period) for period in self.periods]
        phaseCf = [(periodCf[ci] * self.phases[ci]) for ci in range(len(self.levels))]
        print(f'{periodCf=}, {phaseCf=}')
        #FIXME доделать генерацию меандра

        edge = self.position.length * self.dutyCycle
        highBegin = int(1.0 - edge)
        highEnd = int(edge)
        _phase = self.position.length - int(self.position.length * self.phase)

        for i in range(self.position.length):
            x = (i + _phase) % self.position.length
            self.buffer.append(self.lowv if x < highBegin or x > highEnd else self.highv)


class GenGradGen(GradGen):
    """Генератор, возвращающий значения от вложенных генераторов.

    Внимание! Поля экземпляра класса GenGradGen (position и т.п.)
    могут не использоваться классами-потомками."""

    def __init__(self, **kwargs):
        self.generators = []
        super().__init__(**kwargs)

    def get_disp_name(self):
        return '%s(%s)' % (self.name, ', '.join([gen.get_disp_name() for gen in self.generators]))

    def subgen_added(self):
        """При необходимости каких либо действий после добавления
        вложенных генераторов этот метод должен быть перекрыт классом-
        потомком."""

        pass

    def add_subgen(self, *gen):
        """Добавление одного или нескольких вложенных генераторов.

        gen - экземпляр(ы) класса GradGen."""

        self.generators += gen

        self.position.set_length(self.generators)

        self.subgen_added()

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


class RepeaterGenGradGen(GradGen):
    """Генератор, повторяющий вызов дочернего генератора указанное
    количество раз.
    Не является потомком GenGradGen, несмотря на название класса.
    Наследственное поле "position" используется только как хранилище
    количества повторов, position.mode игнорируется."""

    def __chk_subgen(self, gen):
        if not isinstance(gen, GradGen):
            raise ValueError('invalid "gen" parameter type (must be subclass of GradGen)')

        return gen

    def __init__(self, **kwargs):
        self.itersleft = 0
        self.subgen = self.__chk_subgen(kwargs.get('subgen', None))
        self.__accum = None

        super().__init__(**kwargs)

    def get_disp_name(self):
        return '%s(%s)' % (self.name, self.subgen.get_disp_name())

    def set_subgen(self, gen):
        self.subgen = self.__chk_subgen(gen)
        self.__setup_iters_left()

    def get_n_values(self):
        return self.subgen.get_n_values() * self.position.length

    def __setup_iters_left(self):
        self.itersleft = self.get_n_values()

    def reset(self):
        super().reset()
        self.subgen.reset()
        self.__setup_iters_left()

    def get_next_value(self):
        if self.itersleft > 0:
            self.__accum = self.subgen.get_next_value()
            self.itersleft -= 1

        return self.__accum


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

    def get_disp_name(self):
        return '%s(%s)' % (self.name, self.activeGen.get_disp_name())

    def reset(self):
        super().reset()
        self.__set_active_gen()

    def subgen_added(self):
        if not self.activeGen:
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
    DEFAULT_TICK_INTERVAL = 1000/30  # 30 fps в миллисекундах
    DEFAULT_UNIVERSE = 1

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
        fixrange    - булевское значение; если True - значения, выдаваемые
                      генераторами, принудительно загоняются в допустимый
                      диапазон (см. описание функции grad_values_to_array);
        stop        - булевское значение, флаг прекращения работы цикла
                      в методе run()."""

    def __init__(self, **kwargs):
        self.wrapper = ClientWrapper()

        self.generator = kwargs.get('generator')
        self.universe = kwargs.get('universe', self.DEFAULT_UNIVERSE)
        self.iterations = kwargs.get('iterations', None)
        self.interval = kwargs.get('interval', self.DEFAULT_TICK_INTERVAL)
        self.fixrange = kwargs.get('fixrange', False)

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

        # вот какого хера в питоне нет просто нормальных массивов?
        values = unwrap_lol(self.generator.get_next_value())
        data = array('B', map(lambda i: int(255 * (0 if i < 0 else i if i <= MAX_VALUE else MAX_VALUE)),
                              values))

        self.display(values, self.generator)

        self.wrapper.Client().SendDmx(self.universe, data, self.__DMX_sent)

    def display(self, values, gen):
        """При необходимости отображения текущих значений и прочей
        информации этот метод должен быть перекрыт классом-потомком.
        Параметры:
            values  - линейный список float в диапазоне 0.0-1.0;
            gen     - экземпляр GradGen."""

        #print('sending: %s, iteration(s) left: %d' % (data, self.iterations))
        pass

    def blackout(self, nchannels=512):
        """Отправка во все каналы нулей для гашения всех чортовых лампочек.
        Mожет использоваться в обработчиках ошибок, дабы в случае чего
        лампочки ток не жрали зря."""

        if nchannels < 1:
            nchannels = 1
        elif nchannels > 512:
            nchannels = 512

        self.wrapper.Client().SendDmx(self.universe,
            array('B', [0] * nchannels),
            self.__DMX_sent)

    def run(self):
        self.stop = False
        self.wrapper.AddEvent(self.interval, self.__DMX_send_frame)
        self.wrapper.Run()


if __name__ == '__main__':
    print('[debugging %s]' % __file__)

