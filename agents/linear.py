import numpy as np
import agent
import random as rd
import math
import tools


class LinearAgent(agent.Agent):

    def __init__(self, n=4, actions=[-1, 1], score_function=lambda x: 0, epsilon=0.05, H=5):

        self.n = n
        self.actions = actions

        self.x = np.zeros([self.n + 1, 0])
        self.y = np.zeros([self.n, 0])

        self.A = np.identity(self.n)
        self.B = np.zeros([self.n, 1])

        self.measured_X = None
        self.last_action = None

        self.H = H
        self.epsilon = epsilon
        self.score = score_function

    def simulate(self, X, a):
        return self.A * X + a * self.B

    def value(self, s, r):
        c = self.score(s)
        if r == 0:
            return c
        cost = math.inf
        for a in self.actions:
            xx = self.simulate(s, a)
            cost = min(cost, c + self.value(xx, r - 1))
        return cost

    def convert_obs(self, obs):
        return np.matrix(obs).T

    def convert_action(self, a):
        return (a + 1) // 2

    def act(self, obs):
        z = 0.0000000001
        c_x = 2.4
        c_x = 1
        c_theta = 0.2
        Q = np.diag([1. / (c_x ** 2), 0, 1. / (c_theta ** 2), 0])
        eps_square = np.random.rand(4, 4) * z
        eps_square_2 = np.random.rand(4, 4) * z
        eps_col = np.random.rand(4, 1) * z
        eps_col_2 = np.random.rand(4, 1) * z
        c = tools.LQR(self.A + eps_square, self.B + eps_col, Q + eps_square_2, 20)
        x = self.convert_obs(obs) + eps_col_2
        u = c.solve(x)

        a = -1
        if u.item(0) > 0:
            a = 1

        if rd.random() < self.epsilon:
            a = rd.choice(self.actions)

        self.last_action = a

        return self.convert_action(a)

    def old_act(self, obs):
        s = self.convert_obs(obs)

        action = None
        current_v = math.inf
        for a in self.actions:
            x = self.simulate(s, a)
            v = self.value(x, self.H)
            if v < current_v:
                current_v = v
                action = a

        if rd.random() < self.epsilon:
            action = rd.choice(self.actions)

        self.last_action = action

        return self.convert_action(action)

    def update(self, obs, reward, done):
        Y = self.convert_obs(obs)
        if not (self.measured_X is None):
            X = self.measured_X
            X = np.vstack([X, self.last_action])
            self.x = np.hstack([self.x, X])
            self.y = np.hstack([self.y, Y])
            r = np.linalg.lstsq(self.x.T, self.y.T, rcond=None)
            # print(r[1:])
            p = r[0]
            (self.A, self.B) = (p[:-1].T, p[-1].T)
        self.measured_X = Y

    def new_episode(self, obs):
        self.measured_X = None
