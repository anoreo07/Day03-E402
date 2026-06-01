import sys, importlib, os
ROOT = os.path.abspath(os.path.dirname(__file__))
print('ROOT=', ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
importlib.invalidate_caches()
try:
    import src
    print('src package path=', getattr(src, '__path__', None))
    import importlib
    import importlib.util
    spec = importlib.util.find_spec('src.data')
    print('spec for src.data =', spec)
    d = importlib.import_module('src.data')
    print('module file=', getattr(d,'__file__', None))
    print('has load_products=', hasattr(d, 'load_products'))
    print('attrs=', [n for n in dir(d) if n.lower().startswith('load') or 'coupon' in n.lower() or 'product' in n.lower()])
except Exception as e:
    print('IMPORT ERROR:', type(e).__name__, e)
