"""Options pricing models: Black-Scholes, Binomial Tree, Monte Carlo."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


class BlackScholes:
    """Closed-form Black-Scholes pricing for European options.

    Parameters
    ----------
    S : float – Spot price
    K : float – Strike price
    T : float – Time to expiration (years)
    r : float – Risk-free rate (annualized, e.g. 0.05)
    sigma : float – Volatility (annualized, e.g. 0.20)
    """

    @staticmethod
    def _d1d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return d1, d2

    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """European call price."""
        if T <= 0:
            return max(S - K, 0.0)
        d1, d2 = BlackScholes._d1d2(S, K, T, r, sigma)
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)

    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """European put price."""
        if T <= 0:
            return max(K - S, 0.0)
        d1, d2 = BlackScholes._d1d2(S, K, T, r, sigma)
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

    @staticmethod
    def greeks(S: float, K: float, T: float, r: float, sigma: float) -> dict:
        """Compute option Greeks (call-side delta/theta/rho).

        Returns dict with keys: delta, gamma, theta, vega, rho.
        """
        if T <= 0:
            delta = 1.0 if S > K else 0.0
            return {"delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

        d1, d2 = BlackScholes._d1d2(S, K, T, r, sigma)
        sqrt_T = math.sqrt(T)

        delta = _norm_cdf(d1)
        gamma = _norm_pdf(d1) / (S * sigma * sqrt_T)
        theta = (
            -(S * _norm_pdf(d1) * sigma) / (2.0 * sqrt_T)
            - r * K * math.exp(-r * T) * _norm_cdf(d2)
        )
        vega = S * _norm_pdf(d1) * sqrt_T
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2)

        return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


class BinomialTree:
    """Cox-Ross-Rubinstein binomial tree pricer.

    Supports European and American options.
    """

    def __init__(self, steps: int = 100) -> None:
        self.steps = steps

    def price(
        self,
        option_type: str,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        american: bool = False,
    ) -> float:
        """Price an option using the binomial tree method.

        Parameters
        ----------
        option_type : 'call' or 'put'
        american : if True, allow early exercise
        """
        n = self.steps
        dt = T / n
        u = math.exp(sigma * math.sqrt(dt))
        d = 1.0 / u
        p = (math.exp(r * dt) - d) / (u - d)
        disc = math.exp(-r * dt)

        is_call = option_type.lower() == "call"

        # Terminal payoffs
        prices = np.array([S * u**j * d ** (n - j) for j in range(n + 1)])
        if is_call:
            values = np.maximum(prices - K, 0.0)
        else:
            values = np.maximum(K - prices, 0.0)

        # Backward induction
        for i in range(n - 1, -1, -1):
            values = disc * (p * values[1:] + (1 - p) * values[:-1])
            if american:
                prices_i = np.array([S * u**j * d ** (i - j) for j in range(i + 1)])
                if is_call:
                    exercise = np.maximum(prices_i - K, 0.0)
                else:
                    exercise = np.maximum(K - prices_i, 0.0)
                values = np.maximum(values, exercise)

        return float(values[0])


class MonteCarloPricer:
    """Monte Carlo option pricer with customizable payoff functions."""

    def __init__(self, simulations: int = 10000, seed: int | None = None) -> None:
        self.simulations = simulations
        self.seed = seed

    def price(
        self,
        option_type: str,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        payoff_fn=None,
    ) -> dict:
        """Price a European option via Monte Carlo simulation.

        Parameters
        ----------
        payoff_fn : optional callable(S_T, K) -> payoff.
            If None, standard call/put payoff is used.

        Returns dict with price, std_error, confidence_interval (95%).
        """
        rng = np.random.default_rng(self.seed)
        z = rng.standard_normal(self.simulations)
        S_T = S * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)

        if payoff_fn is not None:
            payoffs = np.array([payoff_fn(s, K) for s in S_T])
        elif option_type.lower() == "call":
            payoffs = np.maximum(S_T - K, 0.0)
        else:
            payoffs = np.maximum(K - S_T, 0.0)

        discounted = payoffs * math.exp(-r * T)
        price = float(np.mean(discounted))
        std_error = float(np.std(discounted, ddof=1) / math.sqrt(self.simulations))
        ci = (price - 1.96 * std_error, price + 1.96 * std_error)

        return {"price": price, "std_error": std_error, "confidence_interval": ci}
