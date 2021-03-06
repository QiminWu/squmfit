from __future__ import division
import operator
import numpy as np
import scipy.optimize
import six

# While taking the docstrings from numpy's ufuncs looks good on paper,
# in practice these functions are sometimes provided by mock and therefore less
# than helpful
_use_numpy_docs = True

def model(func):
    """
    Transforms a function to ensure that all of its parameters are
    evaluated. Calls to the transformed function will result in an
    :class:`Expr` when any of its parameters are ``Exprs``.
    """
    def go(*args, **kwargs):
        import inspect
        is_expr = any(isinstance(v, Expr) for v in kwargs.values()) or \
                  any(isinstance(v, Expr) for v in args)
        if is_expr:
            call_args = inspect.getcallargs(func, *args, **kwargs)
            return FuncExpr(func, **call_args)
        else:
            return func(*args, **kwargs)

    go.__doc__  = func.__doc__
    return go

def lift_term(value):
    if isinstance(value, Expr):
        return value
    else:
        return Constant(value)

def ufunc1(func):
    def go(x, out=None):
        if out is not None:
            raise ValueError("squmfit.Expr ufuncs don't support output arrays")
        return OpExpr(func, x)

    if _use_numpy_docs:
        go.__doc__ = func.__doc__.split('\n\n')
    return go

def ufunc2(func):
    def go(x1, x2, out=None):
        if out is not None:
            raise ValueError("squmfit.Expr ufuncs don't support output arrays")
        return OpExpr(func, x1, x2)
    return go

class Expr(object):
    """
    An expression capable of taking parameters from a packed parameter
    vector. All of the usual Python arithmetic operations are
    supported as well as a good fraction of the Numpy ``ufuncs``. Note,
    however, that the ufuncs' ``out`` parameter is not supported.
    """

    def evaluate(self, params, **user_args):
        """
        Evaluate the model with the given parameter values.

        :type params: array, shape = [n_params]
        :param params: Packed parameters vector

        :type user_args: kwargs
        :param user_args: Keyword arguments from user
        """
        raise NotImplementedError()

    @property
    def gradient(self):
        """
        The gradient of the expression with respect to the fitted
        parameters or raise a :class:`ValueError` if not applicable.

        :rtype: :class:`Expr` evaluating to array of shape ``(Nparams,)``
        """
        return FiniteDiffGrad(self)

    def parameters(self):
        """
        Return the set of fitted parameters used by this expression.

        :rtype: :class:`set` of :class:`FittedParam`.
        """
        raise NotImplementedError()

    def map(self, f):
        """
        Lift a function into an :class:`Expr`.

        :type f: Function of type `A -> B`
        :param f: The function to lift.
        :returns: Given an :class:`Expr` evaulating to a value of type `A` and a function `A -> B`,
          returns an :class:`Expr` of type `B`.
        """
        return FuncExpr(f, self)

    def __getitem__(self, k):
        return OpExpr(operator.getitem, self, lift_term(k))

    def __neg__(self):
        return OpExpr(operator.neg, self)

    def __add__(self, other):
        return OpExpr(operator.add, self, lift_term(other))

    def __radd__(self, other):
        return OpExpr(operator.add, lift_term(other), self)

    def __sub__(self, other):
        return OpExpr(operator.sub, self, lift_term(other))

    def __rsub__(self, other):
        return OpExpr(operator.sub, lift_term(other), self)

    def __mul__(self, other):
        return OpExpr(operator.mul, self, lift_term(other))

    def __rmul__(self, other):
        return OpExpr(operator.mul, lift_term(other), self)

    def __truediv__(self, other):
        return OpExpr(operator.truediv, self, lift_term(other))

    def __rtruediv__(self, other):
        return OpExpr(operator.truediv, lift_term(other), self)

    def __div__(self, other):
        return OpExpr(operator.floordiv, self, lift_term(other))

    def __rdiv__(self, other):
        return OpExpr(operator.floordiv, lift_term(other), self)

    def __pow__(self, other):
        return OpExpr(operator.pow, self, lift_term(other))

    def __rpow__(self, other):
        return OpExpr(operator.pow, lift_term(other), self)

    # numpy ufuncs
    # Math operations
    add          = ufunc2(np.add)
    subtract     = ufunc2(np.subtract)
    multiply     = ufunc2(np.multiply)
    divide       = ufunc2(np.divide)
    logaddexp    = ufunc2(np.logaddexp)
    logaddexp2   = ufunc2(np.logaddexp2)
    true_divide  = ufunc2(np.true_divide)
    floor_divide = ufunc2(np.floor_divide)
    negative     = ufunc1(np.negative)
    power        = ufunc2(np.power)
    remainder    = ufunc2(np.remainder)
    mod          = ufunc2(np.mod)
    fmod         = ufunc2(np.fmod)
    absolute     = ufunc1(np.absolute)
    rint         = ufunc1(np.rint)
    sign         = ufunc1(np.sign)
    conj         = ufunc1(np.conj)
    exp          = ufunc1(np.exp)
    log          = ufunc1(np.log)
    log2         = ufunc1(np.log2)
    log10        = ufunc1(np.log10)
    expm1        = ufunc1(np.expm1)
    log1p        = ufunc1(np.log1p)
    sqrt         = ufunc1(np.sqrt)
    square       = ufunc1(np.square)
    reciprocal   = ufunc1(np.reciprocal)

    # Trigonometric functions
    sin     = ufunc1(np.sin)
    cos     = ufunc1(np.cos)
    tan     = ufunc1(np.tan)
    arcsin  = ufunc1(np.arcsin)
    arccos  = ufunc1(np.arccos)
    arctan  = ufunc1(np.arctan)
    arctan2 = ufunc2(np.arctan2)
    hypot   = ufunc2(np.hypot)
    sinh    = ufunc1(np.sinh)
    cosh    = ufunc1(np.cosh)
    tanh    = ufunc1(np.tanh)
    arcsinh = ufunc1(np.arcsinh)
    arccosh = ufunc1(np.arccosh)
    arctanh = ufunc1(np.arctanh)
    deg2rad = ufunc1(np.deg2rad)
    rad2deg = ufunc1(np.rad2deg)

    # Comparison functions
    greater       = ufunc2(np.greater)
    greater_equal = ufunc2(np.greater_equal)
    less          = ufunc2(np.less)
    less_equal    = ufunc2(np.less_equal)
    not_equal     = ufunc2(np.not_equal)
    equal         = ufunc2(np.equal)
    logical_and   = ufunc2(np.logical_and)
    logical_or    = ufunc2(np.logical_or)
    logical_xor   = ufunc2(np.logical_xor)
    logical_not   = ufunc2(np.logical_not)
    maximum       = ufunc2(np.maximum)
    minimum       = ufunc2(np.minimum)
    fmax          = ufunc2(np.fmax)
    fmin          = ufunc2(np.fmin)

    # Floating functions
    floor     = ufunc1(np.floor)
    ceil      = ufunc1(np.ceil)
    trunc     = ufunc1(np.trunc)

class FiniteDiffGrad(Expr):
    """ The gradient of an expression computed by finite difference """
    def __init__(self, expr):
        """
        Create an expression representing the gradient of an expression.

        :type expr: :class:`Expr`
        :param expr: The expression to differentiate.
        """
        self.expr = expr

    def evaluate(self, params, **user_args):
        # Parameters:
        # Reduce step until relative chance drops below this
        delta_thresh = 0.1
        # Reduce step by this factor
        alpha = 10

        f0 = expr.evaluate(params, **user_args)
        grad = np.empty(len(params))

        for i in range(len(params)):
            # Start with a reasonable step size
            h = abs(params[i]) / 10
            g0 = 1/0
            while h:
                p1 = params[:]
                p1[i] += h
                f1 = expr.evaluate(p1, **user_args)

                g = (f1 - f0) / h
                if abs(g - g0) < g * thresh:
                    grad[i] = g1
                    break
                else:
                    h /= alpha
                    g0 = g

                if h < 1e-12:
                    grad[i] = 0
                    break

        return grad

    def parameters(self):
        return self.expr.parameters()

    def __str__(self):
        return 'Grad(%s)' % str(self.expr)

class EvaluationError(Exception):
    def __init__(self, expr, inner):
        self.expr = expr
        self.inner = inner

    def __str__(self):
        return "Encountered error during evaluation of %s:\n %s" % (self.expr, self.inner)

class FuncExpr(Expr):
    """
    An expression which calls a function.

    Any arguments which are :class:`Expr` objects will be evaluated
    with :class:`Expr.evaluate` before being passed to the function.

    This is essentially a wrapper lifting function application into
    the `Expr` functor.
    """

    def __init__(self, func, *args, **kwargs):
        """
        Create an expression which calls the provided function with
        the provided arguments. Any arguments which are :class:`Expr`
        objects will be evaluated with :class:`Expr.evaluate` before
        being passed on to the function.

        :param func: The function to call.
        :param args: Ordered arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def evaluate(self, params, **user_args):
        def eval_term(value):
            if isinstance(value, Expr):
                return value.evaluate(params, **user_args)
            else:
                return value
        try:
            eval_args = map(eval_term, self.args)
            eval_kwargs = {k: eval_term(v) for k,v in six.iteritems(self.kwargs)}
            return self.func(*eval_args, **eval_kwargs)
        except Exception as e:
            raise EvaluationError(self, e)

    def parameters(self):
        accum = set()
        for p in self.args:
            if isinstance(p, Expr):
                accum.update(p.parameters())
        for p in self.kwargs.values():
            if isinstance(p, Expr):
                accum.update(p.parameters())
        return accum

    def __str__(self):
        args = [str(arg) for arg in self.args]
        kwargs = ['%s=%s' % (k, str(v)) for k,v in self.kwargs.items()]
        return "%s(%s)" % (self.func.__name__, ', '.join(args + kwargs))

class OpExpr(Expr):
    """ A helper used by arithmetic operations """
    def __init__(self, op, *operands):
        self.op = op
        self.operands = operands

    def evaluate(self, params, **user_args):
        return self.op(*[model.evaluate(params, **user_args) for model in self.operands])

    def parameters(self):
        accum = set()
        accum.update(*[a.parameters() for a in self.operands])
        return accum

    def __str__(self):
        return "%s(%s)" % (self.op.__name__, ', '.join(str(o) for o in self.operands))

class Constant(Expr):
    """ An :class:`Expr` containing a constant value """
    def __init__(self, value):
        """
        Create a constant-valued :class:`Expr`

        :param value: The value
        """
        self.value = value

    def evaluate(self, params, **user_args):
        return self.value

    def parameters(self):
        return set()

    def __str__(self):
        return str(self.value)

class Argument(Expr):
    """
    An :class:`Expr` which evaluates to a keyword argument passed at
    evaluation-time.
    """
    def __init__(self, name):
        self.name = name

    def evaluate(self, params, **user_args):
        return user_args[self.name]

    def parameters(self):
        return set()

    def __str__(self):
        return "Argument(%s)" % self.name
