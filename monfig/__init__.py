# Constants
from ._monfig import default, Optional, Allow
from ._monfig import Required, Mandatory
from ._monfig import Final, Disabled
from ._monfig import CONFIG

# Classes
from ._monfig import TreeConstraint, GeneralConstraint, FutureConstraint 
from ._monfig import TypeConstraint, RangeConstraint, StringPatternConstraint
from ._monfig import Context, _ContextManager
ContextManager = _ContextManager

# Functions
from ._monfig import build_tag
from ._monfig import shortcut, condition
from ._monfig import OR, AND
from ._monfig import BEGIN, END
from ._monfig import current_context

# Abbreviations
tC = TreeConstraint
fC = GeneralConstraint
ftC = FutureConstraint
TpC = TypeConstraint
RgC = RangeConstraint
ptC = StringPatternConstraint
C = condition