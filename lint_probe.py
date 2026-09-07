def a(p):
    with open(p, 'w') as f:          # literal mode
        f.write('x')

def b(p, overwrite):
    with open(p, 'w' if overwrite else 'a') as f:   # computed mode - as in PySnooper
        f.write('x')
