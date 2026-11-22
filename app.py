
import flask as _fl
for _v in list(globals().values()):
    if isinstance(_v, _fl.Flask):
        app = _v
        break
