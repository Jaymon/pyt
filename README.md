# Pyt 

Pyt is a lightweight wrapper around [Python's unittest module](https://docs.python.org/3/library/unittest.html) that adds some nice features and enhancements over the stock `unittest` module.


### Quickstart

Pyt overrides unittest's built-in pathfinding to be smarter and less verbose, so you can match tests using prefix matching which makes running a test like:

	$ python -m unittest tests.foo_test.BarTestCase.test_che
	
as simple as:

	$ pyt foo.Bar.che
	
But it's even less verbose if you want it to be, pyt can reach into the modules and classes to do its matching, so you don't even need to specify the module and class if you don't want to:

	$ pyt che


#### More examples

To run all the `Happy` tests:

    $ pyt Happy

To run all the `newmodule` tests:

    $ pyt newmodule

To run more than one test:

    $ pyt test1 test2 ...

To run every test `pyt` can find:

    $ pyt

And the way I like to run all tests in the current directory:

    $ pyt -vb
    
Which can also be written:

	$ pyt --verbose --buffer


### Flags

To see everything pyt can do

    $ pyt --help
    
#### --warnings

This will convert warnings into errors.

	$ pyt --warnings
	
#### --rerun

If your last testrun had failing tests this will rerun only the tests that failed.

	$pyt --rerun


### Things to be aware of

#### pyt uses Python's PEP 8 style conventions

`pyt` uses [Python's code styling conventions](http://www.python.org/dev/peps/pep-0008/) to decide what is the module and class, so, given input like this:

    $ pyt foo.bar.Baz.che

`pyt` will consider `foo.bar` to be the module, `Baz` to be a class (because it starts with a capital letter), and `che` to be a method (since it comes after the class).

Likewise, `pyt` uses unittest conventions, so a test module should end with `_test` (eg, `foo.bar_test`) or start with test (eg, `test_foo.py`) and a TestCase class should extend `unittest.TestCase`, and test methods should start with `test_` (eg, `test_che`).


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


#### Environment Variables

If you are running the tests within pyt, you might notice there is an environment variable `PYT_TEST_COUNT` that contains the count of how many tests pyt found to run.


## Installation

Use `pip`:

    $ pip install pyt

You can also get it directly from the repo:

    $ pip install --upgrade git+https://github.com/Jaymon/pyt#egg=pyt


## Testing

Testing in 3.5 on MacOS:

    $ python3.10 -m unittest pyt_test

Or, if you're really brave, you can use `pyt` to test itself:

    $ python -m pyt tests -df

