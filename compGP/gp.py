import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from math import sqrt
from main.coreGP import CoreGP

epsilon = 0.00000001


class GP:

    def __normalizeSigma(self, sigma):
        if sigma < 0.1 * epsilon:
            print("ALERT: SMALL SIGMA", sigma)
            return (np.random.random() + 0.1) * epsilon
        return sigma

    def __init__(self, k, i, n, m=1, debug=True, scipy=False):

        self.k = k  # kernel function
        self.i = i  # ith component
        self.n = n  # dimension of state space
        self.m = m  # dimension of action space

        self.X = None
        self.Y = None
        self.N = None

        self.gp = CoreGP(scipy=scipy, k=k)

        self.debug = debug

    def fit(self, X, Y):
        self.gp.train(X, Y)

    def computePik(self, S, inter):
        # S = [S_0, S_1, ..., S_{k-1}]
        # S_0 is a singleton containing x_0
        # S_i = [S_i^0, ..., S_i^n]
        # S_i^j = (a, b)

        # self.__description(S)

        f, approx_f = self.__createComputeFixedPik(inter)
        start = self.__startingPointFromSets(S)
        bounds = self.__packSets(S)
        x, y = self.__minimize(f, start, bounds)
        xx, yy = self.__minimize(approx_f, start, bounds)
        # print("REAL F", x, f(x))
        # print("APPROX F", xx, f(xx))
        yy = f(xx)
        if yy < y:
            x, y = xx, yy
        return f, x, y

    def synthesizeSet(self, S, p=0.95):
        # S = [S_0, S_1, ..., S_{k-1}]
        # S_0 is a singleton containing x_0
        # S_i = [S_i^0, ..., S_i^n]
        # S_i^j = (a, b)

        # self.__description(S)

        m = self.__createM(p, bigM=False)
        M = self.__createM(p, bigM=True)

        start = self.__startingPointFromSets(S)
        bounds = self.__packSets(S)
        a = self.__minimize(m, start, bounds)
        b = self.__maximize(M, start, bounds)

        # print("Resulting set: ", [a, b])

        return [a[1], b[1]]

    def __probInter(self, mu=0, sigma=1, inter=[-1.96, 1.96]):
        return norm.cdf(inter[1], mu, sqrt(sigma)) - norm.cdf(inter[0], mu, sqrt(sigma))

    def __extractMuSigma(self, xs):
        # xs = [x_0, ..., x_{k-1}]
        # x_i = np.matrix([[], ..., []])
        # x_i is a concatenation of state and action

        k = len(xs)

        MU, SIGMA = self.gp.predict(xs, return_cov=True)

        if self.debug:
            print("BIG MU SIGMA", MU, SIGMA)
            print("k", k)

        if k == 1:
            return MU.item(0), SIGMA.item(0)

        MU_1 = MU[np.ix_(range(k-1))]
        MU_2 = MU[np.ix_([k-1])]

        SIGMA_11 = SIGMA[np.ix_(range(k-1), range(k-1))]
        SIGMA_12 = SIGMA[np.ix_(range(k-1), [k-1])]
        SIGMA_21 = SIGMA[np.ix_([k-1], range(k-1))]
        SIGMA_22 = SIGMA[np.ix_([k-1], [k-1])]

        prod = SIGMA_21 * np.linalg.inv(SIGMA_11)
        x = np.matrix([xx[self.i] for xx in xs[1:]]).T

        if self.debug:
            print("x", x)

        mu = MU_2 + prod * (x - MU_1)
        sigma = SIGMA_22 - prod * SIGMA_12

        if self.debug:
            print("small mu sigma", mu, sigma)

        # TODO detect epsilon
        return mu.item(0), self.__normalizeSigma(sigma.item(0))

    def __unpack(self, xx):
        length = self.n + self.m
        k = len(xx) // length
        x = [[xx[i * length + j] for j in range(length)] for i in range(k)]
        if self.debug:
            print("UNPACKED", x)
        return x

    def __getAlpha(self, p=0.95):
        return norm.ppf(0.5 * (1. + p))

    def __createM(self, p=0.95, bigM=True):
        alpha = [self.__getAlpha(p)]  # array so nonlocal
        # print("ALPHA", alpha[0])

        if bigM:
            def f(packed_xs):
                # xs = [x_0, ..., x_{k-1}]
                # x_i is a concatenation of the state and the action
                xs = self.__unpack(packed_xs)
                mu, sigma = self.__extractMuSigma(xs)
                return mu + alpha[0] * sqrt(sigma)
        else:
            def f(packed_xs):
                # xs = [x_0, ..., x_{k-1}]
                # x_i is a concatenation of the state and the action
                xs = self.__unpack(packed_xs)
                mu, sigma = self.__extractMuSigma(xs)
                return mu - alpha[0] * sqrt(sigma)

        return f

    def __createComputeFixedPik(self, inter):
        # xs = [x_0, ..., x_{k-1}]
        # x_i is a concatenation of the state and the action
        # inter = [a, b]
        # returns P[a <= X_k^i <= b] when X_0 = x_0, ..., X_{k-1} = x_{k-1}

        def f(packed_xs):
            xs = self.__unpack(packed_xs)
            mu, sigma = self.__extractMuSigma(xs)
            if self.debug:
                print("MU, SIGMA", mu, sigma)
            p = self.__probInter(mu, sigma, inter)
            return p

        def approx_f(packed_xs):
            xs = self.__unpack(packed_xs)
            mu, sigma = self.__extractMuSigma(xs)
            if self.debug:
                print("MU, SIGMA", mu, sigma)
            p = self.__probInter(mu, sigma, inter)
            p *= 1000
            p -= ((inter[0] - mu) / sigma) ** 2
            p -= ((inter[1] - mu) / sigma) ** 2
            return p

        return f, approx_f

    def __getCenter(self, s):
        # s = S_i = [(a_1, b_1), ..., (a_{n+m}, b_{n+m})]
        return [0.5 * (ss[0] + ss[1]) for ss in s]

    def __packSets(self, old_S):
        S = []
        for s in old_S:
            for ss in s:
                S.append(ss)
        return S

    def __startingPointFromSets(self, S):
        # S = [S_0, S_1, ..., S_{k-1}]
        # S_0 is a singleton containing x_0
        # S_i = [S_i^1, ..., S_i^{n+m}]
        # S_i^j = (a, b)
        x = []
        for s in S:
            x += self.__getCenter(s)
        return np.array(x)

    def __minimize(self, f, start, bounds, N=1000):
        x, y = start, f(start)

        def compare(x, y, xx):
            yy = f(xx)
            if yy <= y:
                return xx, yy
            return x, y

        for _ in range(N):
            xx = [np.random.uniform(inter[0], inter[1]) for inter in bounds]
            x, y = compare(x, y, xx)

        r = minimize(f, x, bounds=bounds)
        x, y = compare(x, y, r['x'])

        return x, y

    def __maximize(self, f, start, bounds, N=1000):

        def new_f(x):
            return - f(x)

        x, y = self.__minimize(new_f, start, bounds, N=N)
        return x, -y

    def __description(self, S):
        print("This sequence of sets:", S)
        y = [s[self.i] for s in S]
        for i in range(len(S) - 1):
            print(str(S[i]) + " -> " + str(y[i+1]))
