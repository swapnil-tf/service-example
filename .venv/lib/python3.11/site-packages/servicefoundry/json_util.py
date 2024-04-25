import datetime


def json_default_encoder(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    raise TypeError(f"Cannot json encode {type(o)}: {o}")
