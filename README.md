# monfig-python
An interesting library to leverage python module for configuration and its checks

## Introduction

This library is a toy project to leverage pythonic magic code to help use python module as configuration and do check for that like pylance.

The configurations are defined in a module using variable assignment, and checks are done by using another module which defines a rule set contains some constraints using annotations.

This way can simplify the setting and parsing of configurations.

The original intention of this project is to create a pseudo language based on python grammar but looked like another language.

## Usage
Only tested features and apis are listed. Other developing features can be found in the [__init__.py](monfig/__init__.py) file and the [tests](tests).

### Contexts
Context is the code chunk between BEGIN and END.

Only configurations newly defined (or overridden) in a Context will be included in the check.

A module without BEGIN and END is regarded as a Context but will not trigger the check. However, these modules can still be a rule set.

Actually this feature supports not only modules but also classes, functions and objects but they are not tested.

### Define a Context

`monfig.CONFIG` is the default global context manager and we can use it to create a Context.

`CONFIG.BEGIN`, `CONFIG.BEGIN = ruleset`, `CONFIG.BEGIN = (ruleset, options)` and `monfig.BEGIN(ruleset, options)` can all define a BEGIN at where they are placed.

Similarly, `CONFIG.END` can define an END.

When BEGIN and END are defined, code chunk between them is regarded as a Context.

Only Context with a ruleset specified can trigger the check, 
I recommand to use `CONFIG.BEGIN = ruleset` and `CONFIG.END` to define a Context because they are used like keywords.

### Rule set

Rule set contains rules to check the corresponding configuration.

It can be a Context or implicitly defined as a module.

All rules are listed in the rule set using assignment.

### Rule
The grammar of a rule is as follow:
```
NAME: CONSTRAINTS = DEFAULT_VALUE
```

NAME is a identifier that is the same with the global variable in the python module.

CONSTRAINS is a annotation that represents the limits of this configuration entry.

DEFAULT\_VALUE is any object in python and we can import it as the default value using `from <MODULE_OF_RULES> import *`

### Types of Constraints
There are some pre-defined Constraint classes to support basic check of configurations

1. Constraint

The base class of all constraints.

Subclasses inherited from it should implement a match method that accepts a value which is checked and returns a boolean value to indicate if the value match the rule defined by the Constaint.

2. TreeConstraint

The Constraint class to support OR and AND operation, if it has no children, the match method will return `default`, otherwise it returns the results after an operation applied on the values of its children.

3. GeneralConstaint and FutureConstraint

The classes accept a function and its arguments and the match method will apply the function with arguments on the value to be checked.

Arguments of FutureConstraint objects will be overridden to add a ENV keyword argument before the match method is called.

ENV argument contains the contexts and settings of the rule and checked value which are not known when the rule is declared.

4. TypeConstraint

The class implements the check of value's type.

5. RangeConstraint

The class implements the check of value's range.

6. StringPatternConstraint

The class implements the check if a string value matches the given regex pattern.

### Constraints

This annotation can be a object or a list of objects.

The object can be a Constraint or types that are supported by a shortcut function to convert them into Constraint objects.

The annotation will be passed to a condition function which can convert frequently presented objects into Constraint objects.

A raw object that is not list and not Constraint may be converted into Constraint.

A type will be converted into TypeConstraint, a callable will be converted into GeneralConstaint, and a string will be converted into StringPatternConstraint.

The annotation given in list will be converted into a single constriant, but rules inside the list will be apply the AND operation.

Object given in tuple is regarded as a shortcut.

Shortcuts now include multiple types `(type1, type2, ...)`, range `(min, max[, allow_equals])`, function `(func, args[, kwargs])` and regex pattern `(regex, func[, flags])`.

### Special constants

The library contains some constants that have specical value or usage.

1. Required and Mandatory

The value use in the DEFAULT\_VALUE section will require the configuration to define this entry (NAME)

Do not use rule like `Required = Required` and it will be ignored.

To define a entry with name Required, using `Required = Mandatory` can help.

2. default, Optional and Allow

Used in the DEFAULT\_VALUE. No value will break this rule.

3. Final and Disabled

Used in the CONSTRAINTS section. No value can pass this rule.

### Abbreviations

Short names like `C=condition` defined in the `__init__.py` file.

### Functions

See functions section in the `__init__.py` file.

In most time, only condition, BEGIN and END will be used.

### Example

Assuming we define a rule set `rule.py` as follows.

```
from monfig import Required
from monfig import C
config1: [int, (1, 10)] = Required
config2: (int, float, str) = 10
config3: C(int) | C(float) | C(str) = 10
```

The first rules requires the configuration to include a `config1` and it should be a int and the value should be greater than 1 and lower than 10.

The second rule requires the `config2` to be a int or a float or a str if it is defined, otherwise default value 10 is used.

The third rule does the same thing with the second rule.

If we define a configuration as follows.

```
import rule
from rule import *
from monfig import CONFIG
CONFIG.BEGIN = rule
config2 = lambda x:x
CONFIG.END
```
This configuration will be checked when it is imported.

It breaks the rule 1 and 2 because it does not define a `config1` and the type of `config2` is not one of the three given types.

It does not break rule 3 because rule 3 has a default value.

If a configuration passes all rules, it can be used as a normal module and we can access its configuration using `<module>.<config>` after the module is imported.
