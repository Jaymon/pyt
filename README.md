# Pyt -- easy python testing for unittest tests

So here was my problem, I would work on big Python projects, and I would be adding a new file to a module in the 
big project, for example, my new file might be something like this:

    /project/foo/bar/che/baz/newmodule.py

I would be adding the `Happy` class with a `sad` method to `newmodule` and I would want to test it,
so I would then have to add a test for it:

    /project/test/foo/bar/che/baz/newmoduletest.py

Then I would want to test my new class method:

    $ python -m unittest test.foo.bar.che.baz.newmoduletest.HappyTestCase.test_sad

This got really annoying, everytime, I would have to remember the syntax to call unittest from the command line, and then I would
have to remember what I named the test case (let's see, was that `HappyTestCase` or `HappyTest`), so I decided to
take a bit of time and simplify it, that's when `pyt` was born.

With `pyt`, I just need to remember what I'm working on:

    $ pyt Happy.sad

and `pyt` will do the rest, it will check every test module it finds in the working directory and see if it
has a Happy test case with a test sad method. No more having to remember the unittest syntax, no more typing long test paths.
Hopefully, if tests are easy to run, I'll write more of them.

## More examples

Continuing the above example

To run all the `Happy` tests:

    $ pyt Happy

To run all the `newmodule` tests:

    $ pyt newmodule

Run more than one test:

    $ pyt test1 test2 ...

## Things to be aware of

* `pyt` uses Python's PEP standard conventions to decide what is the module and class, so, given input like this:

    $ pyt foo.bar.Baz

`pyt` will consider `Baz` to be a class because it starts with a capital letter.

* `pyt` can fail on vague input and will run the first satisfactory test it finds, so if you have:

    /project
      /user.py
      /foo/user.py

and you run:

    $ pyt user

it will run the first `user_test` it finds, even if you meant a different one, the solution is to just be more
verbose:

    $ pyt foo.user

