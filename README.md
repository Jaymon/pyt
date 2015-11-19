# Pyt 

Easy python testing for Python's unittest module.

Pyt's goal is to make writing and running Python unit tests fun and easy.


## pyt testrunner

So here was my problem, I would work on big Python projects, and I would be adding a new python file to a module in this big project, for example, my new file might be something like this:

    /project/foo/bar/che/baz/newmodule.py

I would be adding the `Happy` class with a `sad` method to `newmodule` and I would want to test it, so I would then have to add a test for it:

    /project/test/foo/bar/che/baz/newmodule_test.py

Then I would want to test my new class method:

    $ python -m unittest test.foo.bar.che.baz.newmodule_test.HappyTestCase.test_sad

This got really annoying! Everytime, I would have to remember the syntax to call unittest from the command line, and then I would have to remember what I named the test case (let's see, was that `HappyTestCase` or `HappyTest`), so I decided to take a bit of time and simplify it, that's when `pyt` was born.

With `pyt`, I just need to remember what I'm working on:

    $ pyt Happy.sad

and `pyt` will do the rest, it will check every test module it finds in the working directory and see if it has a Happy test case with a `test_sad` method. No more having to remember the unittest syntax, and no more typing long test paths. Hopefully, if tests are easy to run, I'll write more of them.


### More examples

Continuing the above example

To run all the `Happy` tests:

    $ pyt Happy

To run all the `newmodule` tests:

    $ pyt newmodule

To run more than one test:

    $ pyt test1 test2 ...

To run every test `pyt` can find:

    $ pyt --all


### Things to be aware of

#### pyt uses Python's PEP 8 style conventions

`pyt` uses [PEP 8](http://www.python.org/dev/peps/pep-0008/) to decide what is the module and class, so, given input like this:

    $ pyt foo.bar.Baz.che

`pyt` will consider `foo.bar` to be modules, `Baz` to be a class because it starts with a capital letter, and `che` to be a method since it comes after a class.


#### pyt turns on buffering and failfast by default

This is the opposite of Python's normal unittest behavior, you can turn them off with `--no-buffer` and `--no-failfast` flags, respectively.

The `--debug` flag is really handy, it will print out each test that pyt runs and how long it took to run it, and how many tests it will run in total.


#### See all flags

To see everything pyt can do

    $ pyt --help


#### Vague input can cause pyt to run more tests than you expect

So if you have something like this:

    project/
      __init__.py
      user.py
      foo/
        __init__.py
        user.py
      tests/
        __init__.py
        user_test.py
        foo/
          __init__.py
          user_test.py

And you want to run tests for `foo.user` and you run:

    $ pyt user

it will run both `tests/user_test` and `tests.foo.user_test`, the solution is to just be more verbose when you have to be:

    $ pyt foo.user


## Installation

Use `pip`:

    $ pip install pyt

You can also get it directly from the repo:

    $ pip install git+https://github.com/Jaymon/pyt#egg=pyt


## TODO

#### Glob support?

add support for globs. Pyt already does prefix searching, but if you wanted to match anything in front:

    pyt mod.Foo.*bar

#### Tests don't run in windows

I used `/` in the tests, and `os.sep` in all the pyt stuff, so it runs on windows, it just doesn't pass the tests :(

