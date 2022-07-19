# dmxgrad

## ВВЕДЕНИЕ

1. Сие поделие является свободным ПО под лицензией [GPL v3](https://www.gnu.org/licenses/gpl.html).
2. Поделие создано и дорабатывается автором исключительно ради собственных
   нужд и развлечения, а также в соответствии с его представлениями об эргономике
   и функциональности.
3. Автор всех видал в гробу и ничего никому не должен, кроме явно
   прописанного в GPL.
4. Несмотря на вышеуказанное, автор совершенно не против, если поделие
   подойдёт кому-то еще, кроме тех, под кем прогорит сиденье из-за пунктов
   с 1 по 3.

## НАЗНАЧЕНИЕ

Небольшой набор костылей для генерации цветовых градиентов, которые
затем могут быть скормлены DMX512-совместимому устройству.

**Внимание!**

  1. Это поделие создано для баловства, и категорически НЕ предназначено
     для управления взаправдашним сценическим оборудованием на взаправдашней
     сцене.
  2. Потроха поделия могут быть в любой момент изменены до полной
     неузнаваемости и несовместимости с предыдущей версией.

## ЧЕГО ХОЧЕТ

  - Python 3.6 или новее
  - демон olad с соответствующими библиотеками
  - пакет ola-python

## КАК ПОЛЬЗОВАТЬСЯ

Насоздавать экземпляров классов, порождённых от GradGen, скормить их
потомку класса GenGradGen, а его, в свою очередь, скормить экземпляру
GradSender.

Пример:
```
sparklegen = SequenceGenGradGen(mode=GradPosition.RANDOM)

for iname in range(1, 4):
    sgN = ImageGradGen(image=Image.open(f'example_sparkle{iname}.png'),
                       mode=GradPosition.REPEAT)
    sparklegen.add_subgen(sgN)

seqgen = SequenceGenGradGen(mode=GradPosition.STOP)

seqgen.add_subgen(ImageGradGen(image=Image.open('example_start.png')),
                  sparklegen,
                  ImageGradGen(image=Image.open('example_completion.png')))

sender = GradSender(generator=seqgen,
                    iterations=seqgen.get_n_values())
sender.run()
sender.blackout()
```

Подробнее - см. help(dmxgrad). Дублировать сюда docstrings из модуля - лень.
