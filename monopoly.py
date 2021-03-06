#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pykov
import math
import networkx as nx
import sympy as sp
import numpy as np
import matplotlib.pyplot as plt
import itertools


def choose(n, k):
    """Compute n choose k.

    :n: Integral number of objects.
    :k: Integral subset size, 0 <= k <= n.
    :returns: Number of ways to place n objects into a set of size k.

    """
    return math.factorial(n) // math.factorial(k) // math.factorial(n - k)


def dicepdf(p, n, s, symbolic=False):
    """
    Compute the probability of obtaining a roll of `p` with `n` `s`-sided dice.

    This probability is more complicated than it would seem.
    See formula (10) in: http://mathworld.wolfram.com/Dice.html

    :p: Integral desired roll in [ndice, 6 * ndice].
    :n: Integral number of dice.
    :s: Integral number of sides on each die.
    :returns: A probability in [0, 1].

    """
    upper_bound = 0
    if symbolic:
        upper_bound = sp.floor(sp.S(p - n) / s) + 1
    else:
        upper_bound = math.floor((p - n) / s) + 1

    c = sum((-1)**k * choose(n, k) * choose(p - s * k - 1, n - 1)
            for k in range(upper_bound))
    if symbolic:
        return sp.S(c) / s**n
    else:
        return c / s**n


def draw_chain(chain, layout="circular"):
    """Draw a Markov chain using networkx.

    :chain: A Pykov chain.
    :returns: Nothing.

    """
    layouts = {"circular": nx.circular_layout, "random": nx.random_layout,
                "shell": nx.shell_layout, "spring": nx.spring_layout,
                "spectral": nx.spectral_layout}
    graph = nx.DiGraph(list(chain.keys()))
    pos = layouts[layout](graph)

    nx.draw_networkx(graph, pos)

def make_numpy_monopoly(size=40, ndice=2, jail=10, goto_jail=30,
                                        chance_spaces=[7, 22, 36]):
    """
    Create a transition matrix for a finite Markov chain representing a
    simplified version of Monopoly. See make_pykov_monopoly() for an
    explanation of our rules.

    We need this method because pykov doesn't allow for easy access to the full
    transition matrix, making it difficult to verify properties such as
    regularity.

    This is a _right_ stochastic matrix, i.e. P[i, j] is the probability of
    moving to state j from state i.
    """

    # Note: Until the very end of this function, P[i, j] means the probability
    # of transitioning from state i to state j. We fix that right at the end by
    # transposing our matrix.

    if jail == goto_jail:
        raise ValueError("`jail` and `goto_jail` must be distinct")

    # Account for three extra jail spaces.
    links = np.zeros((size + 3, size + 3))

    min_advance = ndice
    max_advance = 6 * ndice

    jail_first = size
    jail_second = size + 1
    jail_third = size + 2

    # Probability of rolling one identical number on `ndice`: 6**(-ndice)
    # We have six numbers to choose from, so our probability is 6**(1 - ndice)
    escape_prob = 6**(1 - ndice)

    # Setup the jail rules.
    links[jail_first, jail] = escape_prob
    links[jail_second, jail] = escape_prob

    # Treat the third turn in jail as rolling from jail.
    for advance in range(min_advance, max_advance + 1):
        effect_space = (jail + advance) % size
        links[jail_third, effect_space] = dicepdf(advance, ndice, 6)

    links[jail_first, jail_second] = 1 - escape_prob
    links[jail_second, jail_third] = 1 - escape_prob

    # Establish the rules for the rest of the board.
    for space in range(size):
        if space == goto_jail:
            # Immediately go to jail.
            # (Normally, you wouldn't end up here. This only happens on chance
            # spaces for technical reasons.)
            links[space, jail_first] = 1
        else:
            for advance in range(min_advance, max_advance + 1):
                effect_space = (space + advance) % size

                if effect_space == goto_jail:
                    # Landing on goto_jail is treated as being sent straight to
                    # jail_first.
                    links[space, jail_first] += dicepdf(advance, ndice, 6)
                elif effect_space in chance_spaces:
                    # We land here with probability dicepdf(advance, ndice, 6).
                    base_prob = dicepdf(advance, ndice, 6)

                    # From here, there is a 20/32 chance to stay put.
                    links[space, effect_space] += 20 / 32 * base_prob

                    # There is a 12/32 chance to move from here to a random
                    # spot, including `jail_first`, and excluding `goto_jail`.
                    # Each spot will have a 1/size * 12/32 chance of being
                    # chosen.
                    # Note that there are `size` elements being considered
                    # here.
                    for chosen_space in range(size):
                        if chosen_space == goto_jail:
                            chosen_space = jail_first

                        links[space, chosen_space] += (1 / size * 12 / 32 * base_prob)

                    # Summing up these probabilities, we get:
                    #   20/32 * base_prob + size * 1/size * 12/32 * base_prob
                    # = base_prob * (20/32 + 12 / 32)
                    # = base_prob.
                    # That is, all of the probabilities work out fine.
                else:
                    # Proceed as usual according to the probability of the sum.
                    links[space, effect_space] += dicepdf(advance, ndice, 6)

    # Alright, so we need to fix one thing. The matrix currently has a column
    # and row dedicated to `goto_jail`. Nothing goes there, and we don't want
    # to have it. (It ruins regularity.) Thus, we'll strip its row and its
    # column from the matrix.
    links = np.delete(links, goto_jail, axis=0)
    links = np.delete(links, goto_jail, axis=1)

    return links.T


def make_sympy_monopoly(size=40, ndice=2, jail=10, goto_jail=30,
                        chance_spaces=[7, 22, 36]):
    """
    Create a transition matrix for a finite Markov chain representing a
    simplified version of Monopoly. See make_pykov_monopoly() for an
    explanation of our rules.

    We need this method because pykov doesn't allow for easy access to the full
    transition matrix, making it difficult to verify properties such as
    regularity.

    This is a _right_ stochastic matrix, i.e. P[i, j] is the probability of
    moving to state j from state i.
    """

    # Note: Until the very end of this function, P[i, j] means the probability
    # of transitioning from state i to state j. We fix that right at the end by
    # transposing our matrix.

    if jail == goto_jail:
        raise ValueError("`jail` and `goto_jail` must be distinct")

    # Account for three extra jail spaces.
    links = sp.zeros(size + 3, size + 3)

    min_advance = ndice
    max_advance = 6 * ndice

    jail_first = size
    jail_second = size + 1
    jail_third = size + 2

    # Probability of rolling one identical number on `ndice`: 6**(-ndice)
    # We have six numbers to choose from, so our probability is 6**(1 - ndice)
    escape_prob = sp.S(6)**(1 - ndice)

    # Setup the jail rules.
    links[jail_first, jail] = escape_prob
    links[jail_second, jail] = escape_prob

    # Treat the third turn in jail as rolling from jail.
    for advance in range(min_advance, max_advance + 1):
        effect_space = (jail + advance) % size
        links[jail_third, effect_space] = dicepdf(advance, ndice, 6, symbolic=True)

    links[jail_first, jail_second] = 1 - escape_prob
    links[jail_second, jail_third] = 1 - escape_prob

    # Establish the rules for the rest of the board.
    for space in range(size):
        if space == goto_jail:
            # Immediately go to jail.
            # (Normally, you wouldn't end up here. This only happens on chance
            # spaces for technical reasons.)
            links[space, jail_first] = 1
        else:
            for advance in range(min_advance, max_advance + 1):
                effect_space = (space + advance) % size

                if effect_space == goto_jail:
                    # Landing on goto_jail is treated as being sent straight to
                    # jail_first.
                    links[space, jail_first] += dicepdf(advance, ndice, 6, symbolic=True)
                elif effect_space in chance_spaces:
                    # We land here with probability dicepdf(advance, ndice, 6).
                    base_prob = dicepdf(advance, ndice, 6, symbolic=True)

                    # From here, there is a 20/32 chance to stay put.
                    links[space, effect_space] += sp.S(20) / 32 * base_prob

                    # There is a 12/32 chance to move from here to a random
                    # spot, including `jail_first`, and excluding `goto_jail`.
                    # Each spot will have a 1/size * 12/32 chance of being
                    # chosen.
                    # Note that there are `size` elements being considered
                    # here.
                    for chosen_space in range(size):
                        if chosen_space == goto_jail:
                            chosen_space = jail_first

                        links[space, chosen_space] += (sp.S(1) / size * sp.S(12) / 32 * base_prob)

                    # Summing up these probabilities, we get:
                    #   20/32 * base_prob + size * 1/size * 12/32 * base_prob
                    # = base_prob * (20/32 + 12 / 32)
                    # = base_prob.
                    # That is, all of the probabilities work out fine.
                else:
                    # Proceed as usual according to the probability of the sum.
                    links[space, effect_space] += dicepdf(advance, ndice, 6, symbolic=True)

    # Alright, so we need to fix one thing. The matrix currently has a column
    # and row dedicated to `goto_jail`. Nothing goes there, and we don't want
    # to have it. (It ruins regularity.) Thus, we'll strip its row and its
    # column from the matrix.
    links.row_del(goto_jail)
    links.col_del(goto_jail)

    return links.T

def make_pykov_monopoly(size=40, ndice=2, jail=10, goto_jail=30,
                                        chance_spaces=[7, 22, 36]):
    """Create a Markov chain representing a simplified version of Monopoly.

    Rules:
        - We have `size` spaces, running from 0 to `size` - 1.

        - "Go" is at space 0.

        - At any particular space, we roll `ndice` fair, independent dice, and
          move forward the sum of their rolls.

        - `jail` and `goto_jail` cannot be equal. (Allowing them to be equal
          _and_ obeying the jail rules contradicts the stochastic matrix
          property. We would have P[jail, jail_first] = 1 _and_ P[jail, jail +
          ndice] > 0.)

        - If we land on `goto_jail`, then we move to the special jail states:

            - The special jail states are `jail_first = size`, `jail_second =
              size + 1`, and `jail_third = size + 2`.

            - Landing on `goto_jail` is treated as being sent straight to
              `jail_first`.

            - To leave jail, we have two possibilities:

                - Wait three turns. From the third turn spot, rolling is as if
                  from `jail`.

                - Roll the same thing on every die. There is a 1/6**(ndice -
                  1) probability of this occurring. If this occurs, then we are
                  placed at `jail`. If this does not occur, then we advance to
                  the next turn jail spot.

        - Landing on a space in `chance_spots` triggers special chance rules:

            - With probability 20/32, nothing will happen, and we will stay
              put.

            - With probability 12/32, a space will be chosen (uniformly) at
              random, and we will be moved there. This includes `goto_jail`.
              The reason for allowing `goto_jail` to be chosen is so that the
              resulting transition matrix is still regular, as otherwise the
              chain is not irreducible.

    :ndice: Number of dice we may roll.
    :size: Number of spaces on the board.
    :jail: Space on which the jail is located.
    :goto_jail: Space on which the "goto jail" is located.
    :chance_spaces: Spaces on which the chance card rules are applied.
    :returns: Pykov Chain object.

    """
    if jail == goto_jail:
        raise ValueError("`jail` and `goto_jail` must be distinct")

    links = {(i, j): 0 for (i, j) in itertools.product(range(size + 3), repeat=2)}

    min_advance = ndice
    max_advance = 6 * ndice

    jail_first = size
    jail_second = size + 1
    jail_third = size + 2

    # Probability of rolling one identical number on `ndice`: 6**(-ndice)
    # We have six numbers to choose from, so our probability is 6**(1 - ndice)
    escape_prob = 6**(1 - ndice)

    # Setup the jail rules.
    links[(jail_first, jail)] = escape_prob
    links[(jail_second, jail)] = escape_prob

    # Treat the third turn in jail as rolling from jail.
    for advance in range(min_advance, max_advance + 1):
        effect_space = (jail + advance) % size
        links[(jail_third, effect_space)] = dicepdf(advance, ndice, 6)

    links[(jail_first, jail_second)] = 1 - escape_prob
    links[(jail_second, jail_third)] = 1 - escape_prob

    # Establish the rules for the rest of the board.
    for space in range(size):
        if space != goto_jail:
            for advance in range(min_advance, max_advance + 1):
                effect_space = (space + advance) % size

                if effect_space == goto_jail:
                    # Landing on goto_jail is treated as being sent straight to
                    # jail_first.
                    links[(space, jail_first)] += dicepdf(advance, ndice, 6)
                elif effect_space in chance_spaces:
                    # We land here with probability dicepdf(advance, ndice, 6).
                    base_prob = dicepdf(advance, ndice, 6)

                    # From here, there is a 20/32 chance to stay put.
                    links[(space, effect_space)] += 20 / 32 * base_prob

                    # There is a 12/32 chance to move from here to a random
                    # spot, including `jail_first`.
                    # Each spot will have a 1/size * 12/32 chance of being
                    # chosen.
                    # Note that there are `size` elements being considered
                    # here.
                    for chosen_space in range(size):
                        if chosen_space == goto_jail:
                            # Go directly to jail, not `goto_jail`.
                            chosen_space = jail_first

                        links[(space, chosen_space)] += (1 / size * 12 / 32 * base_prob)

                    # Summing up these probabilities, we get:
                    #   20/32 * base_prob + size * 1/size * 12/32 * base_prob
                    # = base_prob * (20/32 + 12 / 32)
                    # = base_prob.
                    # That is, all of the probabilities work out fine.
                else:
                    # Proceed as usual according to the probability of the sum.
                    links[(space, effect_space)] += dicepdf(advance, ndice, 6)

    return pykov.Chain(links)

def plot_walk_histogram(walks, length, chain, start=None):
    """Plot the histogram of an accumulated walk dictionary.

    :walks: Integral number of walks to take.
    :length: Integral number of steps that each walk should be.
    :chain: Pykov Chain to perform the walk on.
    :start: Start state in `chain` for walk.
    :returns: Nothing.

    """
    walks = walk_accumulate(walks, length, chain, start)
    centered_lefts = [left - .5 for left in walks.keys()]
    plt.bar(centered_lefts, walks.values(), width=1)

def walk_accumulate(walks, length, chain, start=None):
    """Accumulate the results of many walks into a dictionary.

    :walks: Integral number of walks to take.
    :length: Integral number of steps that each walk should be.
    :chain: Pykov Chain to perform the walk on.
    :returns: Dictionary of `{ret: end}` pairs such that `ret[end]` is the
              frequency that the state `end` occured.

    """
    res = {key: 0 for key in chain.states()}

    for walk in range(walks):
        if start:
            stop = chain.walk(length, start)[-1]
        else:
            stop = chain.walk(length)[-1]

        res[stop] += 1

    return res

def space_align(strings):
    """Return strings space-aligned for printing.

    Consider printing this:
        foobar: 0
        bar: 1

    We would rather:
        foobar: 0
           bar: 1

    This is what is meant by space-aligning. We add a space to every string so
    that when printing or appending new strings at the end, they start from the
    same position.

    :strings: List of strings.
    :returns: List of space-aligned strings.

    """
    longest = max(len(s) for s in strings)
    return [" " * (longest - len(s)) + s for s in strings]

def report_steady(chain):
    """
    Print a report on the steady state of the Monopoly chain, assuming that one
    exists.

    :chain: pykov.Chain created by make_pykov_monopoly().
    :returns: Nothing.

    """
    steady = chain.steady()
    jail_spaces = [10, 40, 41, 42]
    jail_prob = sum(steady[j] for j in jail_spaces)
    probs = {"Jail (10)": jail_prob}
    for space in steady.keys():
        if space not in jail_spaces:
            name = standard_monopoly_map[space]
            key = name + " ({})".format(space)
            probs[key] = steady[space]

    print("Steady state probabilities:")

    # Sort probabilities into descending order.
    sorted_pairs = sorted(probs.items(), key=lambda pair: pair[-1],
                          reverse=True)

    sorted_strings = [name for name, prob in sorted_pairs]
    # Align them so that they print pretty.
    sorted_strings = space_align(sorted_strings)

    # sorted_strings does not keep track of the probability, but it is in the
    # same order as sorted_pairs, so we can use the current index to grab the
    # probability.
    for index, aligned_space in enumerate(sorted_strings):
        prob = sorted_pairs[index][-1]
        print("\t{}:".format(aligned_space), prob)


def plot_jail_distance(chain, include_jail=False):
    """TODO: Docstring for jail_distance_plot.

    :chain: TODO
    :returns: TODO

    """
    steady = chain.steady()
    jail_prob = sum(steady[j] for j in JAIL_SPACES)
    xs = [k - JAIL for k in steady.keys() if k not in JAIL_SPACES]
    ys = [steady[k] for k in steady.keys() if k not in JAIL_SPACES]

    if include_jail:
        xs += [0]
        ys += [jail_prob]

    plt.plot(xs, ys, "ro", ms=5)


def expectation_calculation(chain):
    """TODO: Docstring for expectation_calculation.

    :chain: TODO
    :returns: TODO

    """
    steady = chain.steady()
    expecteds = []

    for space in steady:
        if space in standard_monopoly_hotel_costs:
            expected = steady[space] * standard_monopoly_hotel_costs[space]
            expecteds.append((space, expected))

    expecteds = sorted(expecteds, key=lambda pair: pair[-1], reverse=True)

    return expecteds


def plot_expecteds(chain):
    """TODO: Docstring for plot_expecteds.

    :chain: TODO
    :returns: TODO

    """
    expecteds = expectation_calculation(chain)
    xs, ys = list(zip(*expecteds))
    plt.plot(xs, ys, "o", ms=10)
    plt.title("Expected gains versus board number")
    plt.xlabel("Space number")
    plt.ylabel("Expected gains (base rent)")

    ax = plt.gca()
    ax.title.set_fontsize(25)
    ax.xaxis.label.set_fontsize(20)
    ax.yaxis.label.set_fontsize(20)


standard_monopoly_hotel_costs = {
    1: 2,
    3: 4,
    6: 6,
    8: 6,
    9: 8,
    11: 10,
    13: 10,
    14: 12,
    16: 14,
    18: 14,
    19: 16,
    21: 18,
    23: 18,
    24: 20,
    26: 22,
    27: 22,
    29: 24,
    31: 26,
    32: 26,
    34: 28,
    37: 35,
    39: 50
}


standard_monopoly_map = { 0: "GO"
                        , 1: "Mediterranean Avenue"
                        , 2: "Community Chest 1"
                        , 3: "Baltic Avenue"
                        , 4: "Income Tax"
                        , 5: "Reading Railroad"
                        , 6: "Oriental Avenue"
                        , 7: "Chance 1"
                        , 8: "Vermont Avenue"
                        , 9: "Connecticut Avenue"
                        , 10: "Jail"
                        , 11: "St. Charles Place"
                        , 12: "Electric Company"
                        , 13: "States Avenue"
                        , 14: "Virginia Avenue"
                        , 15: "Pennsylvania Railroad"
                        , 16: "St. James Place"
                        , 17: "Community Chest"
                        , 18: "Tennessee Avenue"
                        , 19: "New York Avenue"
                        , 20: "Free Parking"
                        , 21: "Kentucky Avenue"
                        , 22: "Chance 2"
                        , 23: "Indiana Avenue"
                        , 24: "Illinois Avenue"
                        , 25: "B. & O. Railroad"
                        , 26: "Atlantic Avenue"
                        , 27: "Ventnor Avenue"
                        , 28: "Water Works"
                        , 29: "Marvin Gardens"
                        , 30: "Go To Jail"
                        , 31: "Pacific Avenue"
                        , 32: "North Carolina Avenue"
                        , 33: "Community Chest"
                        , 34: "Pennsylvania Avenue"
                        , 35: "Short Line"
                        , 36: "Chance 3"
                        , 37: "Park Place"
                        , 38: "Luxury Tax"
                        , 39: "Boardwalk"
                    }

if __name__ == "__main__":
    monopoly_chain = make_pykov_monopoly(40, 2, 10, 30)
    monopoly_matrix = make_numpy_monopoly(40, 2, 10, 30)

    regular_power = 6
    power = np.linalg.matrix_power(monopoly_matrix, regular_power)
    print("P^{} > 0?".format(regular_power))
    if (power > 0).all():
        print(True)
        report_steady(monopoly_chain)
    else:
        print(False)
        print("No steady state to compute.")
