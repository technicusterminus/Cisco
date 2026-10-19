# Was gibt das aus? (Exceptions)
def laden(d, key):
    try:
        return d[key] / 2
    except KeyError:
        return "fehlt"
    except TypeError:
        return "Typ"
    finally:
        print("fertig", key)
print(laden({"a": 10}, "a"))
print(laden({"a": 10}, "b"))
print(laden({"a": "x"}, "a"))
