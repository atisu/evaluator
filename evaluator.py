#!/usr/bin/env python

import sys
import time
import multiprocessing
import copy
from asteval import Interpreter, make_symbol_table


class TimeoutException(Exception):
    """ It took too long to compile and execute. """


class RunnableProcessing(multiprocessing.Process):
    """ Run a function in a child process.

    Pass back any exception received.
    """
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func,) + args
        multiprocessing.Process.__init__(self, target=self.run_func, 
            args=args, kwargs=kwargs)

    def run_func(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self.queue.put((True, result))
        except Exception as e:
            self.queue.put((False, e))

    def done(self):
        return self.queue.full()

    def result(self):
        return self.queue.get()


def timeout(seconds, force_kill=True):
    """ Timeout decorator using Python multiprocessing.

    Courtesy of http://code.activestate.com/recipes/577853-timeout-decorator-with-multiprocessing/
    """
    def wrapper(function):
        def inner(*args, **kwargs):
            now = time.time()
            proc = RunnableProcessing(function, *args, **kwargs)
            proc.start()
            proc.join(seconds)
            if proc.is_alive():
                if force_kill:
                    proc.terminate()
                runtime = time.time() - now
                raise TimeoutException('timed out after {0} seconds'.format(runtime))
            assert proc.done()
            success, result = proc.result()
            if success:
                return result
            else:
                raise result
        return inner
    return wrapper


@timeout(0.5)
def evaluate(eval_code, input_variables={}, output_variables=[]):
    """Evaluates a given expression, with the timeout given as decorator.

    Args:
        eval_code (str): The code to be evaluated.
        input_variables (dict): dictionary of input variables and their values.
        output_variables (array): array of names of output variables.

    Returns:
        dict: the output variables or empty.

    """
    # FIXME: use_numpy the process blocks infinitely at the return statement
    sym = make_symbol_table(use_numpy=False, range=range, **input_variables)
    aeval = Interpreter(
        symtable = sym,
        use_numpy = False,
        no_if = False,
        no_for = False,
        no_while = False,
        no_try = True,
        no_functiondef = True,
        no_ifexp = False,
        no_listcomp = True,
        no_augassign = False, # e.g., a += 1
        no_assert = True,
        no_delete = True,
        no_raise = True,
        no_print = True)
    aeval(eval_code)
    symtable = {x: sym[x] for x in sym if x in output_variables}
    return symtable


if __name__ == "__main__":

    # Example 1
    code_example_1 = """
y = 0
for i in range(10000):
    y = y + i
x = 5
"""
    values_1 = evaluate(code_example_1, output_variables=['x', 'y'])
    print("Example 1: Output variables: {}".format(values_1))
    assert values_1['x'] == 5, "x value should be 5"
    assert values_1['y'] == 49995000, "y value should be 49995000"

    # Example 2
    code_example_2 = """
for i in range(101):
    y = y + i
"""
    values_2 = evaluate(code_example_2, input_variables={'y': 10},
        output_variables=['y'])
    print("Example 2: Output variables: {}".format(values_2))
    assert values_2['y'] == 5060, "y value should be 5060"

