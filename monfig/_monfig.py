import collections.abc
import numbers
import sys
import re
import collections
import operator
import threading
import pickle
default = object()
Required = object()
Mandatory = object()
Optional = default

def build_tag(code, frame=None):
    return f'{code.co_filename}#{code.co_name}'

def get_frame(depth=2):
    f = sys._getframe(depth)
    context_tag = build_tag(f.f_code)
    return context_tag, f.f_locals

def complex_shortcut(v: tuple):
    return default

def shortcut(v: tuple):
    # implement shortcuts
    length = len(v)
    if not length:
        raise RuntimeError(f'At least 1 argument in {v} is required')
    if length < 2:
        return condition(v[0])
    if all(map(lambda x:isinstance(x, type), v)):
        # types shortcut
        return TypeConstraint(*v)
    if length not in (2, 3):
        return complex_shortcut(v)
    # range shortcut
    range_args = {}
    if isinstance(v[0], numbers.Number) and \
        isinstance(v[1], numbers.Number) and \
        (length == 2 or isinstance(v[2], bool)):
        if v[0] is not default:
            range_args['min'] = v[0]
        if v[1] is not default:
            range_args['max'] = v[1]
        if length == 3:
            range_args['allow_equals'] = v[2]
    if range_args:
        return RangeConstraint(**range_args)
    # function shortcut
    if callable(v[0]) and \
        isinstance(v[1], collections.abc.Iterable) and \
        (length == 2 or isinstance(v[2], dict)):
        return GeneralConstraint(v[0], *v[1], **(v[2] if length == 3 else {}))
    if isinstance(v[0], str) and \
        isinstance(v[1], str) and \
        (length == 2 or isinstance(v[2], int)):
        kwargs = {
            'pattern': v[0],
            'match_func': v[1]
        }
        if length == 3:
            kwargs['flags'] = v[2]
        return StringPatternConstraint(**kwargs)
    return default

def condition(v):
    """
    Function to convert a single object into constraint
    Dynamic argument is not supported to avoid conflicts
    Shortcuts are implemented in this function
    """
    if isinstance(v, Constraint):
        return v
    # a class may also be callable
    # so we should check if it is type
    # before checking callable
    if isinstance(v, type):
        return TypeConstraint(v)
    if callable(v):
        return GeneralConstraint(v)
    if isinstance(v, str):
        return StringPatternConstraint(v)
    if isinstance(v, tuple):
        rt = shortcut(v)
        if rt is not default:
            return rt
    elif isinstance(v, collections.abc.Iterable):
        # do not allow not matched shortcuts to be
        # interpreted as AND to avoid misoperation
        iterator = iter(v)
        first = condition(next(iterator))
        for c in iterator:
            first = first & condition(c)
        return first
    raise RuntimeError(f'Not supported type {type(v)}. Try to create constraint manually')

def OR(*args):
    iterator = iter(args)
    first = condition(next(iterator))
    for c in iterator:
        first = first | condition(c)
    return first

def AND(*args):
    return condition(list(args))

def extend_or_append(l, l_or_not):
    if isinstance(l_or_not, list):
        l.extend(l_or_not)
    else:
        l.append(l_or_not)

DEFAULT_ERROR = 'UNKNOWN'
class Constraint:
    """
    Base class of all rules
    """
    def __init__(self, *args, **kwargs):
        self._lock = threading.RLock()
        self.error = DEFAULT_ERROR

    def lock(self, blocking=True, timeout=-1):
        self._lock.acquire(blocking, timeout)

    def release(self):
        self._lock.release()

    def set_error(self, msg):
        if isinstance(self.error, list):
            extend_or_append(self.error, msg)
        else:
            self.error = msg

    def get_error(self):
        return self.error

    def match(self, value):
        raise NotImplementedError('This method should be implemented by subclasses')

    def merge(self, obj, op=operator.or_):
        if not isinstance(obj, Constraint):
            return None
        if isinstance(self, FutureConstraint) or isinstance(obj, FutureConstraint):
            c = FutureConstraint(default)
            c.set_children(self, obj)
            c.set_op(op)
        else:
            c = TreeConstraint(self, obj, op)
        return c

    def __or__(self, obj):
        c = self.merge(obj, op=OPERATOR_OR)
        return self | condition(obj) if c is None else c

    def __ror__(self, obj):
        return self | obj

    def __and__(self, obj):
        c = self.merge(obj, op=OPERATOR_AND)
        return self & condition(obj) if c is None else c
    
    def __rand__(self, obj):
        return self & obj

class _Disabled(Constraint):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def match(self, value):
        return False

class _Enabled(Constraint):
    def __init__(self):
        super().__init__()
        self.error = 'ALLOW'

    def match(self, value):
        return True

Final = _Disabled('is final')
Disabled = _Disabled('is not allowed')
Allow = _Enabled()

OPERATOR_OR = 0
OPERATOR_AND = 1
class TreeConstraint(Constraint):
    def __init__(self, left, right, op):
        self.set_children(left, right)
        self.set_op(op)
        super().__init__()

    def set_children(self, left: Constraint, right: Constraint):
        self.left = left
        self.right = right

    def set_op(self, op):
        self.op = op

    def match(self, value):
        if self.left is None and self.right is None:
            return default
        msg = []
        self.left.lock()
        rl = self.left.match(value)
        if rl and self.op == OPERATOR_OR:
            return rl
        if not rl:
            extend_or_append(msg, self.left.error)
            if self.op == OPERATOR_OR:
                msg.append('OR')
        self.left.release()
        self.right.lock()
        rr = self.right.match(value)
        if rr and self.op == OPERATOR_OR:
            return rr
        if not rr:
            extend_or_append(msg, self.right.error)
        self.right.release()
        # F or F, F and F, F and T, T and T
        if self.op == OPERATOR_OR:
            _msg = ['BEGIN_OR']
            _msg.extend(msg)
            _msg.append('END_OR')
            self.set_error(_msg)
            return False
        if not msg:
            return True
        self.set_error(msg)
        return False

class GeneralConstraint(TreeConstraint):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        super().__init__(None, None, None)

    def match(self, value):
        r = super().match(value)
        if r is default:
            try:
                r = self.func(value, *self.args, **self.kwargs)
                if not r and self.error is DEFAULT_ERROR:
                    self.set_error(f'could not pass function {self.func.__qualname__}')
            except Exception as e:
                msg = [str(e)]
                extend_or_append(msg, self.error)
                self.set_error(msg)
                r = False
        return r

class FutureConstraint(GeneralConstraint):
    def __init__(self, func, *args, **kwargs):
        super().__init__(func, *args, **kwargs)
        self.set_env(None)

    def set_env(self, env):
        self.ENV = env

    def match(self, value):
        if self.left is None and self.right is None:
            if self.ENV is None:
                raise ValueError(f'ENV of {self} is not set')
            self.kwargs['ENV'] = self.ENV
        else:
            if isinstance(self.left, FutureConstraint):
                self.left.set_env(self.ENV)
            if isinstance(self.right, FutureConstraint):
                self.right.set_env(self.ENV)
        return super().match(value)

def get_types_name(t):
    return f"({', '.join(map(lambda x:getattr(x, '__name__', str(x)), t))})"

class TypeConstraint(GeneralConstraint):
    def __init__(self, *expected_types, strict=False):
        self.expected_types = expected_types
        func = lambda v:isinstance(v, expected_types)
        if strict:
            def func(v):
                _t = type(v)
                for t in expected_types:
                    if _t == t:
                        return True
                return False
        super().__init__(func)
        self.error = f'should match one of the types in {get_types_name(expected_types)}'

class RangeConstraint(GeneralConstraint):
    def __init__(self, min=float('-inf'), max=float('inf'), allow_equals=False):
        self.min = min
        self.max = max
        self.allow_equals = allow_equals
        def compare(v):
            if allow_equals:
                if v == max or v == min:
                    return True
            return min < v and v < max
        super().__init__(compare)
        _e = ['[', ']'] if allow_equals else ['(', ')']
        self.error = f'should be in range {_e[0]}{self.min}, {self.max}{_e[1]}'

class StringPatternConstraint(GeneralConstraint):
    def __init__(self, pattern, match_func='fullmatch', flags=0):
        self.pattern = pattern
        self.p = re.compile(pattern, flags)
        self.match_func = match_func
        super().__init__(getattr(self.p, match_func))
        self.error = f'should match pattern "{self.pattern}" (f={self.match_func}, flags={flags})'

class RulesBrokenError(RuntimeError):
    pass

ERR_MESSAGE = '[{}] {}'
ANNOTATIONS_KEY = '__annotations__'
def to_context(obj, manager=default):
    if manager is default:
        manager = CONFIG
    if not isinstance(obj, type) and callable(obj):
        # functions have no local scope unless they are running
        tag = build_tag(obj.__code__)
        if tag not in manager.contexts:
            raise RuntimeError(f'No context is found for {obj}')
        return manager.contexts[tag]
    elif not isinstance(obj, Context):
        # for modules and classes
        return Context(dict(obj.__dict__))

class Context:
    def __init__(self, configs: dict, rules=default, default_rule=Allow):
        self.rules = rules
        self.default_rule = default_rule
        self.configs = configs.copy()
        self.annotations = configs.get(ANNOTATIONS_KEY, {})
        self.updated = False

    def update(self, configs: dict, keep_configs=False):
        self.annotations = configs.get(ANNOTATIONS_KEY, {})
        if keep_configs:
            self.configs.update(configs)
        else:
            configs = configs.copy()
            for name in self.configs.keys() & configs.keys():
                if configs[name] == self.configs[name]:
                    configs.pop(name, default)
            self.configs = configs
        self.updated = True

    def validate(self, manager=default):
        if self.rules is default:
            raise RuntimeError('Rules field is not set')
        context = to_context(self.rules, manager)
        messages = []
        defaults = context.configs
        ruleset = context.annotations
        configs = self.configs
        # apply rules
        for config in configs:
            val = configs[config]
            rule = ruleset.get(config, self.default_rule)
            matcher = condition(rule)
            if isinstance(matcher, FutureConstraint):
                ENV = {
                    'rule_name': config,
                    'rule': rule,
                    'rule_val': defaults.get(config),
                    'context': self,
                    'rule_context': context
                }
                matcher.set_env(ENV)
            with matcher._lock:
                m = matcher.match(val)
            if m:
                continue
            _err = matcher.error
            if not isinstance(matcher, TreeConstraint):
                if _err is DEFAULT_ERROR:
                    _err = f'could not match constraint {matcher}'
                messages.append(ERR_MESSAGE.format(config, _err))
                continue
            if isinstance(_err, str):
                messages.append(ERR_MESSAGE.format(config, _err))
            elif isinstance(_err, list):
                for msg in _err:
                    messages.append(ERR_MESSAGE.format(config, msg))
        # check rules
        if defaults.get('Required', default) is Required:
            defaults.pop('Required')
        if defaults.get('Mandatory', default) is Mandatory:
            defaults.pop('Mandatory')
        for config in defaults:
            if not config in configs:
                v = defaults[config]
                if v is Required or v is Mandatory:
                    messages.append(ERR_MESSAGE.format(config, 'missing required configuration'))
        return messages

    def dump(self, f, manager=default):
        _context = Context({})
        _context.configs = self.configs
        _context.annotations = self.annotations
        _context.default_rule = self.default_rule
        _context.updated = self.updated
        _context.rules = to_context(self.rules, manager)
        if isinstance(f, str):
            f = open(f, 'wb')
        try:
            pickle.dump(_context, f)
            return
        except Exception as e:
            print(f'Warning: skip rules field because of {e}')
            _context.rules = None
        try:
            pickle.dump(_context, f)
        finally:
            f.close()

def error(header, messages):
    msg = [f'Configuration at {header} breaks rules']
    msg.extend(messages)
    raise RulesBrokenError("\n".join(msg))

class _ContextManager:
    __slots__ = ('BEGIN', 'END', 'contexts', 'current_contexts', 'last_closed_context')
    def __init__(self):
        self.contexts = {}
        self.last_closed_context = None
        self.current_contexts = set()
    
    def notify_open(self, tag):
        self.current_contexts.add(tag)

    def notify_close(self, tag):
        self.current_contexts.discard(tag)
        self.last_closed_context = tag

    def has_context(self, tag):
        return tag in self.contexts

    def get_context(self, tag):
        return self.contexts.get(tag)

    def add_context(self, tag, context):
        self.contexts[tag] = context
        self.notify_open(tag)

def process_args(rules, rules_opt):
    manager = CONFIG
    if isinstance(rules, _ContextManager):
        manager = rules
        rules = rules_opt
        if isinstance(rules, tuple):
            if len(rules) > 2:
                raise TypeError(f'Expected 2 arguments but {len(rules)} was given')
            rules_opt = rules[1]
            rules = rules[0]
        else:
            rules_opt = {}
    if rules_opt is default:
        rules_opt = {}
    if not isinstance(rules_opt, dict):
        raise TypeError(f'Options should be dict but was {type(rules_opt)}')
    return rules, rules_opt, manager

def BEGIN(rules=default, rules_opt=default):
    rules, rules_opt, manager = process_args(rules, rules_opt)
    tag, attrs = get_frame() 
    if manager.has_context(tag) and not rules_opt.get('force', False):
        # the class does not support reopen currently
        raise RuntimeError(f'Configuration {tag} exists')
    manager.add_context(
                        tag,
                        Context(attrs,
                                rules,
                                rules_opt.get('default_rule', Allow))
                        )

def END(rules=default, rules_opt=default):
    rules, rules_opt, manager = process_args(rules, rules_opt)
    tag, attrs = get_frame() 
    if not manager.has_context(tag):
        raise RuntimeError(f'Configuration {tag} does not exist')
    context: Context = manager.get_context(tag)
    if context.updated and not rules_opt.get('force', False):
        raise RuntimeError(f'Calling END multiple times is not permitted')
    if rules is not default:
        context.rules = rules
    context.update(attrs)
    if context.rules is not default or rules_opt.get('force_validate', False):
        msg = context.validate(manager)
        if msg:
            error(tag, msg)
    manager.notify_close(tag)

_ContextManager.BEGIN = property(BEGIN, BEGIN)
_ContextManager.END = property(END, END)

CONFIG = _ContextManager()

def current_context():
    return CONFIG.get_context(get_frame()[0])
