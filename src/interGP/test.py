from interGP.gp import GP
import numpy as np
from interGP.compGP import CompGP
from misc import tools


# x : n * 1, y : n * 1
# exponential
def k(x, y):
    s = 0.0
    assert (len(x) == len(y)), "Not same length"
    n = len(x)
    for i in range(n):
        s += (x[i] - y[i]) ** 2
    return np.exp(-0.5 * s)


def trainGP(n=100, debug=True):

    np.random.seed(8)

    def f(x):
        return x[0] * x[1]

    X = [[np.random.rand() * 10, np.random.rand() * 10] for i in range(100)]
    Y = [f(xx) for xx in X]

    gp = GP(k, 0, n=2, m=0, debug=debug)
    gp.fit(X, Y)

    return gp


def testSmallGP(x=2, y=2, noise=0.1, inter=[3.5, 4.5]):
    gp = trainGP()
    return gp.computePik([[(x - noise, x + noise), (y - noise, y + noise)]], inter)


def testGPComposed(x=2, y=2, noise=0.01, inter=[3.8, 4.2], zero=True, debug=True):
    gp = trainGP(debug=debug)
    S_0 = [(1, 1), (2, 2)]
    S_1 = [(2 - noise, 2 + noise), (1 - noise, 1 + noise)]
    S_2 = [(x - noise, x + 2 * noise), (y - noise, y + 2 * noise)]
    S_3 = [(x - noise, x + noise), (y - noise, y + noise)]
    if zero:
        print("Should give 0", gp.computePik([S_0, S_1, S_2, S_3], inter))
    else:
        print("Should give 1", gp.computePik([S_0, S_1, S_3], inter))


def testSynthesizer(x=2, y=2, noise=0.1, p=0.95, debug=True, zero=True):
    gp = trainGP(debug=debug)
    S_0 = [(x, x), (1, 1)]
    S_1 = [(x - noise, x + 2 * noise), (y - noise, y + 2 * noise)]
    S_2 = [(x - noise, x + noise), (y - noise, y + noise)]
    if zero:
        print(gp.synthesizeSet([S_0, S_1, S_2], p))
    else:
        print(gp.synthesizeSet([S_0, S_2], p))


def f_dynamic(x, u):
    return [x[0] + 0.03 * x[1] ** 2, x[1] - 0.1 * x[0]]


def trainCompGP(
        n=200, debug=True, scipy=False,
        f=f_dynamic, n_in=2, amp=10, m=1):

    np.random.seed(8)

    X = [[np.random.rand() * amp for _ in range(n_in)] for i in range(n)]
    U = [[np.random.rand() * 0 for _ in range(m)] for i in range(n)]
    Y = [f(xx, u) for xx, u in zip(X, U)]

    cgp = CompGP(k, n_in, 1, debug=debug, scipy=scipy)

    cgp.fit(X, U, Y)

    return cgp


def doubleTestCompGP(
        x=1.1, y=1.1, noise=0.1, p=0.95, debug=False,
        steps=5, scipy=False):

    cgp = trainCompGP(debug=debug, scipy=scipy)
    U = [[0] for _ in range(steps)]

    S, probs = cgp.synthesizeSets([x, y], U, steps, p)
    print(cgp.computeProbTraj(S, U))


def scipyGP():

    def f(x):
        return x[0] * x[1]

    X = [[np.random.rand() * 10, np.random.rand() * 10] for i in range(100)]
    Y = [f(xx) for xx in X]

    gp = tools.GaussianProcesses()
    gp.train(X, Y)

    return gp


def testCompGPAll(x=1, noise=0., p=0.95, debug=False, steps=5, scipy=True):

    def f(x, u):
        return [x[0] * x[0]]

    cgp = trainCompGP(debug=debug, scipy=scipy, n_in=1, f=f, amp=2, m=1)
    U = [[0] for _ in range(steps)]

    S, probs = cgp.synthesizeSets([x], U, steps, p)
    print(cgp.computeProbTraj(S, U))

testCompGPAll()
