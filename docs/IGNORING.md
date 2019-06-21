# Ignoring Tests

A common pattern I use is I have a module in my tests directory that only contains common base tests that should be run by specific implementations or interfaces, something like:

```python
# __init__.py

from unittest import TestCase

class BaseTestCase(TestCase):
    interface_class = None
    
    def test_thing1(self): pass
    def test_thing2(self): pass
```

Then, I have specific implementations:

```python
# foo_test.py

import foo
from . import BaseTestCase

class FooTest(BaseTestCase):
    interface_class = foo.Foo
``` 

But if you just have pyt run all the tests:

	$ pyt -d


It will try and run both `FooTest` (yay!) and `BaseTestCase` (oh no!).

There are two ways to ignore `BaseTestCase`:

1. begin your tests with an underscore
2. define a `load_tests` function in your module

Let's talk about them.


## Underscore your tests

If you begin your test with an underscore then pyt will ignore it:

```python
# __init__.py

from unittest import TestCase

class _BaseTestCase(TestCase):
    # this test will be ignored by pyt
    pass
```

but this is proprietary to pyt, so it might not be a good solution.


## load_tests function

The [load tests protocol](https://docs.python.org/3/library/unittest.html#load-tests-protocol) can be used to ignore tests:

```python
# __init__.py

from unittest import TestCase, TestSuite

class BaseTestCase(TestCase):
    pass

# ignore all the tests in this module    
def load_tests(*args, **kwargs):
    return TestSuite()
```

This might lead to unintended consequences though if using [unittest's discover functionality](https://docs.python.org/3/library/unittest.html#unittest.TestLoader.discover) (pyt does not use discover):

> If the package `__init__.py` defines load_tests then it will be called and discovery not continued into the package

Another potential issue is any submodules that import these tests will try and run them also, so you need to delete those tests in the submodules so they aren't found:

```python
# foo_test.py

import foo
from . import BaseTestCase

class FooTest(BaseTestCase):
    interface_class = foo.Foo

del BaseTestCase
```

That way they won't be picked up when the submodule, or all tests, are ran.