"""Минимальная реализация Ed25519 (RFC 8032): sign/verify без внешних зависимостей.

Используется для подписи манифеста обновления (update_info.json).
Ключи — hex: приватный seed (64 hex) и публичный ключ (64 hex).
"""
import hashlib

P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
I = pow(2, (P - 1) // 4, P)


def _inv(x):
    return pow(x, P - 2, P)


def _sha512(data):
    return hashlib.sha512(data).digest()


def _xrecover(y):
    xx = (y * y - 1) * _inv(D * y * y + 1) % P
    x = pow(xx, (P + 3) // 8, P)
    if (x * x - xx) % P != 0:
        x = (x * I) % P
    if x % 2 != 0:
        x = P - x
    return x


_BY = 4 * _inv(5) % P
_BX = _xrecover(_BY)
_B = (_BX % P, _BY % P, 1, (_BX * _BY) % P)


def _add(p, q):
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = 2 * t1 * t2 * D % P
    z2d = 2 * z1 * z2 % P
    e = b - a
    f = z2d - c
    g = z2d + c
    h = b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _scalarmult(point, scalar):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _encode(point):
    x, y, z, _ = point
    zi = _inv(z)
    x = x * zi % P
    y = y * zi % P
    data = bytearray(y.to_bytes(32, "little"))
    data[31] |= (x & 1) << 7
    return bytes(data)


def _decode(data):
    if len(data) != 32:
        raise ValueError("Ed25519: неверная длина точки")
    y = int.from_bytes(data, "little") & ((1 << 255) - 1)
    if y >= P:
        raise ValueError("Ed25519: y вне поля")
    x = _xrecover(y)
    if (x & 1) != (data[31] >> 7):
        x = P - x
    return (x, y, 1, x * y % P)


def _clamp(h):
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a


def publickey(seed_hex):
    """Публичный ключ (hex) из приватного seed (hex)."""
    a = _clamp(_sha512(bytes.fromhex(seed_hex)))
    return _encode(_scalarmult(_B, a)).hex()


def sign(seed_hex, message):
    """Подпись (hex) сообщения (bytes) приватным seed (hex)."""
    h = _sha512(bytes.fromhex(seed_hex))
    a = _clamp(h)
    pub = _encode(_scalarmult(_B, a))
    r = int.from_bytes(_sha512(h[32:] + message), "little") % Q
    r_point = _encode(_scalarmult(_B, r))
    k = int.from_bytes(_sha512(r_point + pub + message), "little") % Q
    s = (r + k * a) % Q
    return (r_point + s.to_bytes(32, "little")).hex()


def verify(public_hex, message, signature_hex):
    """Проверка подписи. True/False, исключения не пробрасываются."""
    try:
        if len(public_hex) != 64 or len(signature_hex) != 128:
            return False
        pub = bytes.fromhex(public_hex)
        sig = bytes.fromhex(signature_hex)
        point_a = _decode(pub)
        point_r = _decode(sig[:32])
        s = int.from_bytes(sig[32:], "little")
        if s >= Q:
            return False
        k = int.from_bytes(_sha512(sig[:32] + pub + message), "little") % Q
        left = _scalarmult(_B, s)
        right = _add(point_r, _scalarmult(point_a, k))
        return _encode(left) == _encode(right)
    except Exception:
        return False
