# Those are wrapped into tuples so we can use None there
# otherwise the parameterized framework trows an error
# see https://github.com/wolever/parameterized/issues/55#issuecomment-662759561

EMPTY_STRINGS = [("",), ("   ",), (" ",), ("  ",), ("          ",)]
EMPTY_STRINGS_AND_NONE = EMPTY_STRINGS + [(None,)]
NON_STRING_TYPE_ELEMENTS = [(1,), (1.0, ), (["Test"],), (True,)]
NON_STRING_TYPE_ELEMENTS_AND_NONE = NON_STRING_TYPE_ELEMENTS + [(None,)]
NON_BOOL_TYPE_ELEMENTS = [(1,), (1.0, ), (["Test"],), ("String",)]
NON_BOOL_TYPE_ELEMENTS_AND_NONE = NON_BOOL_TYPE_ELEMENTS + [(None,)]
