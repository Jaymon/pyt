# Pyt -- easy python testing for unittest tests

Pyt's goal is to make writing and running Python unit tests fun and easy :)

Currently, there are two main components, the `pyt` command line test runner, and the `Assert` class

## pyt testrunner

So here was my problem, I would work on big Python projects, and I would be adding a new python file to a module in this 
big project, for example, my new file might be something like this:

    /project/foo/bar/che/baz/newmodule.py

I would be adding the `Happy` class with a `sad` method to `newmodule` and I would want to test it,
so I would then have to add a test for it:

    /project/test/foo/bar/che/baz/newmodule_test.py

Then I would want to test my new class method:

    $ python -m unittest test.foo.bar.che.baz.newmodule_test.HappyTestCase.test_sad

This got really annoying! Everytime, I would have to remember the syntax to call unittest from the command line, and then I would
have to remember what I named the test case (let's see, was that `HappyTestCase` or `HappyTest`), so I decided to
take a bit of time and simplify it, that's when `pyt` was born.

With `pyt`, I just need to remember what I'm working on:

    $ pyt Happy.sad

and `pyt` will do the rest, it will check every test module it finds in the working directory and see if it
has a Happy test case with a `test_sad` method. No more having to remember the unittest syntax, no more typing long test paths.
Hopefully, if tests are easy to run, I'll write more of them.

### More examples

Continuing the above example

To run all the `Happy` tests:

    $ pyt Happy

To run all the `newmodule` tests:

    $ pyt newmodule

To run more than one test:

    $ pyt test1 test2 ...

### Things to be aware of

* `pyt` uses Python's [PEP 8](http://www.python.org/dev/peps/pep-0008/) style conventions to decide what is the module and class, so, given input like this:

        $ pyt foo.bar.Baz.che

    `pyt` will consider `foo.bar` to be modules, `Baz` to be a class because it starts with a capital letter, and `che` to be a method
    since it comes after a class.

* `pyt` can fail on vague input and will run the first satisfactory test it finds, so if you have:

        /project
          __init__.py
          /user.py
          /foo/
            __init__.py
            user.py

    and you want to run tests for `foo.user` and you run:

        $ pyt user

    it will run the first `user_test` it finds, even if you meant a different one, the solution is to just be more
    verbose when you have to be:

        $ pyt foo.user

## pyt Assert

This is a helper class designed to make writing assert statements in your test cases a lot more fluid:

    from pyt import Assert
    
    v = 5
    a = Assert(v)

    a == 5 # assertEqual(v, 5)
    a != 5 # assertNotEqual(v, 5)
    a > 5 # assertGreater(v, 5)
    a >= 5 # assertGreaterEqual(v, 5)
    a < 5 # assertLess(v, 5)
    a <= 5 # assertLessEqual(v, 5)
    +a # self.assertGreater(v, 0)
    -a # self.assertLess(v, 0)
    ~a # self.assertNotEqual(v, 0)

    v = "foobar"
    a = Assert(v)

    "foo" in a # assertIn("foo", v)
    "foo not in a # assertNotIn("foo", v)

    a * str # assertIsInstance(v, str)
    a ** str # assertNotIsInstance(v, str)

    a / regex # assertRegexpMatches(v, re)
    a // regex # assertNotRegexpMatches(v, re)

    # assertRaises(ValueError)
    with Assert(ValueError):
        raise ValueError("boom")

    a == False # assertFalse(v)
    a == True # assertTrue(v)

    a.len == 5 # assertEqual(len(v), 5)

    #it even works on attributes of objects
    o = SomeObject()
    o.foo = 1
    a = Assert(o)
    a.foo == 1

## Installation

Use `pip`:

    $ pip install pyt

You can also get it directly from the repo:

    $ pip install git+https://github.com/Jaymon/pyt#egg=pyt

