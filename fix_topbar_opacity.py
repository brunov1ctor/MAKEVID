with open('makevid/qt/widgets.py', encoding='utf-8') as f:
    c = f.read()

# 1. Reduzir gradiente branco que sobrepoe o tint escuro
old = (
    '        grad.setColorAt(0.0,  QColor(255, 255, 255, 28))\n'
    '        grad.setColorAt(0.18, QColor(255, 255, 255, 10))\n'
    '        grad.setColorAt(0.5,  QColor(255, 255, 255, 3))\n'
    '        grad.setColorAt(1.0,  QColor(0,   0,   0,   18))'
)
new = (
    '        grad.setColorAt(0.0,  QColor(255, 255, 255, 10))\n'
    '        grad.setColorAt(0.18, QColor(255, 255, 255, 4))\n'
    '        grad.setColorAt(0.5,  QColor(255, 255, 255, 1))\n'
    '        grad.setColorAt(1.0,  QColor(0,   0,   0,   6))'
)
c2 = c.replace(old, new)
print('grad replaced:', c2 != c)

with open('makevid/qt/widgets.py', 'w', encoding='utf-8') as f:
    f.write(c2)
print('done')
