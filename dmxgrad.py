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


REVISION = 18


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


def unwrap_lol(src, chktype=None):
    """Рекурсивное разворачивание списка списков (и/или кортежей)
    в один линейный список.

    Функция может использоваться генераторами, получающими значения от
    других генераторов (например, от ParallelGenGradGen), а также при
    обработке параметров-списков, передаваемых конструкторам.

    Параметры:
        src     - входной параметр - список/кортеж или одиночное значение;
        chktype - None или кортеж типов для проверки соответствия
                  типа входного параметра; если None - тип не проверяется.

    Функция возвращает линейный список."""

    def __do_check(v):
        if isinstance(chktype, tuple) and not isinstance(v, chktype):
            raise ValueError('unwrap_lol(): invalid parameter type (must be %s)' % (' or '.join(map(lambda c: c.__name__, chktype))))

        return v

    if not isinstance(src, (list, tuple)):
        return [__do_check(src)]

    ret = []

    for v in src:
        if isinstance(v, (list, tuple)):
            ret += unwrap_lol(v)
        else:
            ret.append(__do_check(v))

    return ret


def channels_to_str(channels, barlen=None):
    """Пребразование списка/кортежа, содержащего значения float
    в диапазоне 0.0-1.0 (и/или кортежи с такими значениями) в строку
    с горизонтальными диаграммами и численными значениями (в виде
    шестнадцатиричных чисел в диапазоне 0x00-0xFF).
    Функция предназначена для визуализации при отладке генераторов.

    Параметры:
        channels    - список или кортеж со значениями каналов;
        barlen      - None или целое - длина прогрессбара;
                      Если None или <= 1 - отобража ется одним символом
                      псевдографики, иначе - полосой в barlen символов.

    Функция возвращает строку."""

    __BCHARS = '-+*#'
    __BCCOUNT = len(__BCHARS)

    def __bar1(v):
        blen = int(v * __BCCOUNT)
        if blen >= __BCCOUNT:
            # значение 1.0 при преобразовании приведет к выходу за
            # границу списка, заодно подстрахуемся от кривых значений
            # > 1.0
            blen = __BCCOUNT - 1

        return __BCHARS[blen]

    def __barN(v):
        blen = int(v * barlen)

        return '%s%s' % ('#' * blen, '-' * (barlen - blen))

    barfunc = __bar1 if (barlen is None or barlen <= 1) else __barN

    return '|'.join(map(lambda v: '%.2x %s' % (int(v * 255), barfunc(v)),
                        unwrap_lol(channels)))


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

    __MODES = 4
    __MIN_MODE = 0
    __MAX_MODE = __MODES - 1
    STOP, REPEAT, MIRROR, RANDOM = range(__MODES)

    DEFAULT_TICK_INTERVAL = 1000 / 30  # 30 fps в миллисекундах

    def __init__(self, length=1, mode=STOP, direction=1, interval=DEFAULT_TICK_INTERVAL):
        """Инициализация счётчика положения градиента с указанными
        параметрами.

        Параметры:
            l, interval     - см. описание метода set_length();
            mode, direction - см. описание соотв. полей класса."""

        self.set_length(length, interval)
        self.set_mode(mode)
        self.set_direction(direction)

        self.value = 0

        self.ncycles = 0

    def __repr__(self):
        return repr_to_str(self)

    def set_direction(self, d=1):
        if d == True or d >= 1:
            d = 1
        elif d == False or d < 0:
            d = -1
        else:
            raise ValueError('%s.set_direction(): invalid direction value (must be 1 or -1, or boolean)' % self.__class__.__name__)

        self.direction = d

    def set_mode(self, m=STOP):
        if m < self.__MIN_MODE or m > self.__MAX_MODE:
            raise ValueError('%s.set_mode(): invalid mode value' % self.__class__.__name__)

        self.mode = m

    def set_length(self, l=1, interval=DEFAULT_TICK_INTERVAL):
        """Установка количества значений.

        Параметры:
            l        - положительное целое (количество значений),
                       или кортеж/список/..., длину которого следует использовать,
                       или float - длительность в секундах,
                       или строка в формате '[ЧЧ:[ММ:]СС', которая будет
                       преобразована опять же в секунды;
            interval - None, int или float - количество обращений
                       к устройству DMX512 в секунду;
                       если указано None или значение <= 0 - используется
                       значение по умолчанию (DEFAULT_TICK_INTERVAL),
                       иначе - указанное значение ."""

        if interval is None or interval <= 0:
            interval = self.DEFAULT_TICK_INTERVAL

        __BAD_LENGTH_VALUE = '%s.set_length(): length must be > 0' % self.__class__.__name__

        def __from_seconds(v):
            return round(1000 * v / interval)

        if isinstance(l, int):
            # указано целое значение - абсолютное значение для length
            if l <= 0:
                raise ValueError(__BAD_LENGTH_VALUE)
        elif isinstance(l, float):
            # указано значение в секундах
            l = __from_seconds(l)
        elif isinstance(l, str):
            # указано значение в виде строки ЧЧ:ММ:СС для пересчёта в секунды
            ts = l.split(':', 2)
            l = 0
            m = 1

            while ts:
                l += int(ts.pop()) * m
                m *= 60

            l = __from_seconds(l)
        else:
            # предположительно указан список или другой тип "с длиной",
            # кою длину и используем как значение для поля lentgh
            try:
                l = len(l)
            except:
                raise ValueError('%s.set_length(): invalid type of "l" parameter' % self.__class__.__name__)

        if l < 0:
            raise ValueError(__BAD_LENGTH_VALUE)

        self.length = int(l)

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

    @staticmethod
    def kwargs_get(args, pname, fallback=None, fchkval=None):
        """Получение параметра из словаря.

        Метод предназначен для обработки параметров в конструкторах
        и методах init_attrs().

        Параметры:
            args        - словарь параметров;
            pname       - строка, имя параметра;
            fallback    - значение параметра по умолчанию;
                          fallback=None и в словаре нет соотв. параметра -
                          метод генерирует исключение;
            fchkval     - None или функция (метод) для проверки
                          полученного значения;
                          на входе получает два параметра:
                            1. проверяемое значение;
                            2. название параметра (для сообщений об ошибках);
                          при необходимости функция может приводить
                          совместимые типы значений к требуемым, и/или
                          ограничивать диапазон значения;
                          функция возвращает значение;
                          при ошибках функция должна генерировать исключение.

        Метод возвращает полученное значение."""

        retv = args.get(pname, fallback)
        if retv is None:
            raise ValueError('parameter "%s" is missing' % pname)

        if callable(fchkval):
            retv = fchkval(retv, pname)

        return retv

    @staticmethod
    def check_isgrad(v, pname):
        if not isinstance(v, GradGen):
            raise ValueError('parameter "%s" must be subclass of GradGen' % pname)

        return v

    def init_attrs(self, **kwargs):
        """Обработка параметров.
        Метод вызывается из конструктора класса.
        При необходимости может быть перекрыт классом-потомком,
        в этом случае метод-наследник должен вызывать "предка",
        если требуется обработать "наследственные" параметры."""

        self.position = GradPosition(kwargs.get('length', 1),
            kwargs.get('mode', self.DEFAULT_MODE))

        self.name = kwargs.get('name', '%s%x' % (self.__class__.__name__, id(self)))

    def __init__(self, **kwargs):
        """Параметры: см. список полей экземпляра класса.

        Этот конструктор и конструкторы классов-потомков получают
        параметры в виде словаря kwargs вместо прямого перечисления
        параметров, дабы не заморачиваться при наследовании
        и вызовах super().
        Названия передаваемых параметров должны соответствовать
        названиям полей экземпляра соотв. класса.
        Классам-наследникам собственные конструкторы иметь не обязательно,
        но может понадобиться перекрывать метод init_attrs(), т.к.
        конструктор вызывает метод reset(), которому нужны все правильно
        присвоенные поля."""

        self.init_attrs(**kwargs)
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

    @staticmethod
    def kwargs_get_tof(args, pname, fallback, tolength=None, chkval=None):
        """Получение и нормализация параметра из словаря.

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

    def init_attrs(self, **kwargs):
        super().init_attrs(**kwargs)

        self.clearBuf = kwargs.get('clearBuf', True)
        self.buffer = []

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

    def init_attrs(self, **kwargs):
        """Параметры (в дополнение к "наследственным"):
            channelsFrom, channelsTo (см. описания одноимённых полей);
                их значения могут быть указаны в виде кортежей или преобразованы
                из значений цветов вызовами hls_to_rgb(), str_to_rgb()."""

        super().init_attrs(**kwargs)

        self.channelsFrom = self.kwargs_get_tof(kwargs, 'channelsFrom', (0,), None, check_float_range_1)
        self.channelsTo = self.kwargs_get_tof(kwargs, 'channelsTo', (MAX_VALUE,), len(self.channelsFrom), check_float_range_1)

    def reset(self):
        super().reset()

        _len = self.position.length - 1

        deltas = []
        cvals = []

        for ci, cFrom in enumerate(self.channelsFrom):
            deltas.append((self.channelsTo[ci] - cFrom) / _len)
            cvals.append(cFrom)

        for i in range(self.position.length):
            self.buffer.append(tuple(cvals))

            for ci, cval in enumerate(cvals):
                cvals[ci] = cval + deltas[ci]


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

    def init_attrs(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        super().init_attrs(**kwargs)

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


class GenRecorderGen(BufferedGradGen):
    """Генератор, однократно засасывающий себе в буфер выхлоп
    другого генератора, и воспроизводящий эти значения.

    Предназначен для буферизации выхлопов сложного нагромождения
    вложенных генераторов, если вдруг не хочется их гонять по циклу
    много раз."""

    def init_attrs(self, **kwargs):
        super().init_attrs(**kwargs)

        self.sourcegen = self.kwargs_get(kwargs, 'sourcegen')

    def reset(self):
        super().reset()

        n = self.sourcegen.get_n_values()
        while n > 0:
            self.buffer.append(unwrap_lol(self.sourcegen.get_next_value()))
            n -= 1


class ConstantGradGen(GradGen):
    """Псевдо-генератор, выдающий постоянные значения.

    Поля экземпляра класса:
        values   - кортеж из float в диапазоне 0.0-1.0.

    Счетчик положения не используется."""

    def init_attrs(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        super().init_attrs(**kwargs)

        self.values = self.kwargs_get_tof(kwargs, 'values', (0, ))

    def get_next_value(self):
        return self.values


class NoiseGen(GradGen):
    """Генератор шума.

    Поля экземпляра класса:
        minValues, maxValues
            - кортежи из float в диапазоне 0.0-1.0 с граничными значениями
              для каналов.

    Счетчик положения не используется."""

    def init_attrs(self, **kwargs):
        super().init_attrs(**kwargs)

        self.minValues = self.kwargs_get_tof(kwargs, 'minValues', (0.0, ),
                            None, check_float_range_1)
        self.maxValues = self.kwargs_get_tof(kwargs, 'maxValues', (1.0, ),
                            len(self.minValues), check_float_range_1)

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

    def init_attrs(self, **kwargs):
        """Параметры (в дополнение к наследуемым):
            levels, phases, periods (см. описание полей выше);
            Примечание: вместо кортежей этим параметрам можно присваивать
            по одному значению float, в этом случае параметр будет
            преобразован в кортеж из одного элемента."""

        super().init_attrs(**kwargs)

        self.levels = self.kwargs_get_tof(kwargs, 'levels', (1.0, ), None, check_float_range_1)
        _ll = len(self.levels)

        self.lowLevels = self.kwargs_get_tof(kwargs, 'lowLevels', (0.0, ), _ll, check_float_range_1)

        self.phases = self.kwargs_get_tof(kwargs, 'phases', (0.0, ), _ll, check_float_range_1)

        self.periods = self.kwargs_get_tof(kwargs, 'periods', (1.0, ), _ll, check_float_positive)


class SineWaveGradGen(WaveGradGen):
    """Генератор синусоиды."""

    def reset(self):
        super().reset()

        periodCf = []
        phaseCf = []
        amplCf = []
        sinCf = []

        for ci, level in enumerate(self.levels):
            perlen = self.position.length / self.periods[ci]
            periodCf.append(perlen)
            phaseCf.append(perlen * self.phases[ci])

            amplitude = (level - self.lowLevels[ci]) / 2.0
            amplCf.append((amplitude, level - amplitude))

            sinCf.append(2 * pi / perlen)

        sinOffsetX = pi / 2 # дабы синусоида завсегда начиналась с минимального значения

        for i in range(self.position.length):
            v = []

            for ci, (amplitude, offsetY) in enumerate(amplCf):
                v.append(offsetY - amplitude * sin(sinOffsetX + (i + phaseCf[ci]) * sinCf[ci]))

            self.buffer.append(v)


class SquareWaveGradGen(WaveGradGen):
    """Генератор меандра.

    Поля экземпляра класса (в дополнение к унаследованным):
        dutyCycles  - коэффициенты заполнения для каналов;
                      по умолчанию - 1.0."""

    def init_attrs(self, **kwargs):
        """Параметры: см. описание полей экземпляра класса."""

        super().init_attrs(**kwargs)

        __DEF_DC = 1.0

        self.dutyCycles = self.kwargs_get_tof(kwargs,
            'dutyCycles',
            (__DEF_DC, ),
            len(self.levels),
            check_float_range_1)

    def reset(self):
        super().reset()

        perLengths = []
        posHi0 = []
        posHi1 = []

        nchannels = len(self.levels)

        for ci, level in enumerate(self.levels):
            # длина полного периода
            perlen = self.position.length / self.periods[ci]
            perLengths.append(perlen)

            # длина полуволны с "высоким" уровнем
            hilen = perlen / (1.0 + self.dutyCycles[ci])

            # начало полуволны с "высоким" уровнем
            startHi = perlen * self.phases[ci]
            posHi0.append(startHi)
            # конец полуволны с "высоким" уровнем
            posHi1.append(startHi + perlen - hilen)

        for i in range(self.position.length):
            chns = []

            for ci in range(nchannels):
                v = i % perLengths[ci]

                chns.append(self.levels[ci] if v >= posHi0[ci] and v < posHi1[ci] else self.lowLevels[ci])

            self.buffer.append(chns)


class GroupGenGradGen(GradGen):
    """Надстройка над GradGen, предназначенная для издевательств
    над несколькими равноправными генераторами.

    Поля (в дополнение к наследственным):
        generators  - список экземпляров потомков GradGen."""

    def init_attrs(self, **kwargs):
        """Инициализация полей.

        Параметры:
            subgen  - список экземпляров потомков GradGen."""

        super().init_attrs(**kwargs)

        self.generators = unwrap_lol(kwargs.get('subgen', []), (GradGen,))
        self.subgen_added()

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


class ParallelGenGradGen(GroupGenGradGen):
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


class MixGenGradGen(ParallelGenGradGen):
    """Генератор, складывающий выхлопы вложенных генераторов.

    Количество каналов "выхлопа" определяется количеством каналов
    генератора, у которого их больше всего. Значения от прочих
    генераторов используются циклически."""

    def get_next_value(self):
        accum = [0.0] * self.position.length

        for gen in self.generators:
            genvals = unwrap_lol(gen.get_next_value())
            ngv = len(genvals)

            for ci, accv in enumerate(accum):
                accum[ci] = accv + genvals[ci % ngv]

        for ci, accv in enumerate(accum):
            accum[ci] = accv / self.position.length

        return accum


class RepeaterGenGradGen(GradGen):
    """Генератор, повторяющий вызов дочернего генератора указанное
    количество раз.
    Наследственное поле "position" используется только как хранилище
    количества повторов, position.mode игнорируется.
    Временный класс-костыль до момента переделки Parallel/SequenceGenGradGen."""

    #TODO возможно, имеет смысл переделать класс GenGradGen или Parallel/SequenceGenGradGen так, чтобы в отдельном классе RepeaterGenGradGen пропала необходимость

    def init_attrs(self, **kwargs):
        super().init_attrs(**kwargs)

        self.itersleft = 0
        self.subgen = self.kwargs_get(kwargs, 'subgen', None, self.check_isgrad)
        self.__accum = None

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


class EnvelopeGenGradGen(GradGen):
    """Генератор, амплитудно модулирующий выхлоп одного генератора
    выхлопом другого.

    Внимание! Экспериментальный генератор, может быть перделан
    полностью или удалён!"""

    def init_attrs(self, **kwargs):
        """Инициализация полей.

        Параметры (в дополнение к наследственным):
            sourcegen   - генератор значений, потомок класса GradGen;
            envelopegen - генератор значений огибающей, потомок класса GradGen;
                          если envelopegen.get_next_value() возвращает меньше
                          значений, чем sourcegen.get_next_value() -
                          значения "огибающей" используются циклически
                          до заполнения."""

        super().init_attrs(**kwargs)

        self.sourcegen = self.kwargs_get(kwargs, 'sourcegen', None, self.check_isgrad)
        self.envelopegen = self.kwargs_get(kwargs, 'envelopegen', None, self.check_isgrad)

    def get_next_value(self):
        channels = unwrap_lol(self.sourcegen.get_next_value())
        envels = unwrap_lol(self.envelopegen.get_next_value())

        clen = len(channels)
        elen = len(envels)

        retv = [0.0] * clen

        for ixc, cv in enumerate(channels):
            retv[ixc] = cv * envels[ixc % elen]

        return retv

    def get_disp_name(self):
        return '%s(%s * %s)' % (
                    self.name,
                    self.sourcegen.get_disp_name(),
                    self.envelopegen.get_disp_name())


class CrossfadeGenGradGen(GradGen):
    """Генератор, смешивающий выхлопы двух генераторов с соотношением,
    определяемым третьим генератором.

    Внимание! Экспериментальный генератор, может быть перделан
    полностью или удалён!"""

    def init_attrs(self, **kwargs):
        """Инициализация полей.

        Параметры (в дополнение к наследственным):
            source1gen,
            source2gen  - генераторы исходных значений, потомок класса GradGen;
            balancegen  - генератор значений соотношения (перекрёстного
                          затухания), потомок класса GradGen;
                          выходное значение равно (s1v * (1-bv)) + (s2v * bv).

        Внимание! Количество каналов (значений), возвращаемое методом
        CrossfadeGenGradGen.get_next_value(), определяется количеством
        значений, возвращаемых source1gen.get_next_value(), а значения
        source2gen и balancegen используются циклически до заполнения."""

        super().init_attrs(**kwargs)

        self.source1gen = self.kwargs_get(kwargs, 'source1gen', None, self.check_isgrad)
        self.source2gen = self.kwargs_get(kwargs, 'source2gen', None, self.check_isgrad)
        self.balancegen = self.kwargs_get(kwargs, 'balancegen', None, self.check_isgrad)

    def get_next_value(self):
        src1v = unwrap_lol(self.source1gen.get_next_value())
        src2v = unwrap_lol(self.source2gen.get_next_value())

        balancev = unwrap_lol(self.balancegen.get_next_value())

        s1len = len(src1v)
        s2len = len(src2v)
        blen = len(balancev)

        retv = [0.0] * s1len

        for ixc, s1v in enumerate(src1v):
            bv = balancev[ixc % blen]
            retv[ixc] = (s1v * (1.0 - bv)) + (src2v[ixc % s2len] * bv)

        return retv

    def get_disp_name(self):
        return '%s(%s, %s, %s)' % (
                    self.name,
                    self.source1gen.get_disp_name(),
                    self.source2gen.get_disp_name(),
                    self.balancegen.get_disp_name())


class SequenceGenGradGen(GroupGenGradGen):
    """Генератор, вызывающий вложенные генераторы поочерёдно.
    Количество последовательных вызовов каждого генератора
    соответствует значению соотв. position.length.
    По окончании списка генераторов перебор начинается сначала."""

    def init_attrs(self, **kwargs):
        self.activeGen = None
        self.activeItrs = 0

        super().init_attrs(**kwargs)

    def __set_active_gen(self):
        if self.generators:
            self.activeGen = self.generators[self.position.value]
            self.activeItrs = self.activeGen.get_n_values()
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

        self.activeItrs -= 1

        if self.activeItrs <= 0:
            self.position.next_value()
            self.__set_active_gen()

        return ret


class GradSender():
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
        stop        - булевское значение, флаг прекращения работы цикла
                      в методе run()."""

    def __init__(self, **kwargs):
        self.wrapper = ClientWrapper()

        self.generator = kwargs.get('generator')
        self.universe = kwargs.get('universe', self.DEFAULT_UNIVERSE)
        self.iterations = kwargs.get('iterations', None)
        self.interval = kwargs.get('interval', GradPosition.DEFAULT_TICK_INTERVAL)

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

