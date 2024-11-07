# type: ignore
import monfig
from monfig import Required
from monfig import Mandatory
from monfig import default
from monfig import Final, Disabled

REQUIRED = Required
MANDATORY = Mandatory
FINAL: Final = 10
NOT_ALLOWED: Disabled  = 10
test_type: int = default
test_func: lambda x : x > 5 = default
test_pattern: 'abc[d|e]' = default
test_multiple_and: [int, lambda x : x > 5, lambda x : x < 10] = default
test_range_0: monfig.RangeConstraint(5, 10) = default
test_range_1: monfig.RangeConstraint(5) = default
test_types: (int, float, str) = default
test_range_2: (5, 10) = default
test_range_3: (5, 10, True) = default
test_func_s: (lambda x, y : x > y, (10,)) = default
test_func_s1: (lambda x, y : x > y, [], {'y': 10}) = default
test_pattern_s: ('abc[d|e]',) = default
test_pattern_s1: ('abc[d|e]', 'match') = default
test_or: monfig.OR(int, float) = default
test_and: monfig.AND(int, (5, 10)) = default
test_or_1: monfig.condition(int) | monfig.condition(float) = default
test_and_1: monfig.condition(int) & monfig.condition((5, 10)) = default
test_nested: [monfig.OR(int, float), (5, 10), lambda x:x==6] = default
test_nested_1: [monfig.OR(int, monfig.OR(float, str)), (5, 10)] = default
test_nested_2: [monfig.OR(int, float), (5, 10), lambda x:x==6] = default