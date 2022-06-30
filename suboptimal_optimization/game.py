# %% ######################################################################
###                                                                     ###
###                          Table of Contents                          ###
###                                                                     ###
###     0.          Dependent Libraries                                 ###
###     1.          Variable Initialization                             ###
###     2.0.        Draw Simulation                                     ###
###     2.1.        Game Simulation                                     ###
###     2.2.        Results                                             ###
###                                                                     ###
###########################################################################
###                                                                     ###
###     3.0.        Explanation - Function                              ###
###     3.1.        Explanation - Optimization                          ###
###     3.2.        Explanation - Suboptimization                       ###
###                                                                     ###
###########################################################################
###                                                                     ###
###     Constant-sum and simultaneous game between 2 players.           ###
###     A player will uniformly at random draw a number from [0, 1].    ###
###     If this number is below a pre-determined threshold, then it     ###
###         will be discarded, and a new number will be drawn and kept. ###
###     The 2 players' numbers are compared, and the larger value wins. ###
###     Each player is unaware of each other's threshold.               ###
###                                                                     ###
###     How is the optimal threshold picked?                            ###
###                                                                     ###
###########################################################################



# %% ######################################################################
###     0.          Dependent Libraries                                 ###
###########################################################################

import random
import os, sys
import scipy.stats



# %% ######################################################################
###     1.          Variable Initialization                             ###
###########################################################################

num_game = 10 ** 6
p1_threshold = 0.45

data_dir = os.getcwd()
p2_strategy = {}
for k in ["naive", "greedy", "intuitive", "optimal"]:
    p2_threshold = \
        eval(open(os.path.join(data_dir, f"strategy_{k}.txt")).read())
    p2_strategy[k] = {
        "threshold" : p2_threshold,
        "wins_p1" : 0,
        "wins_p2" : 0,
        }



# %% ######################################################################
###     2.0.        Draw Simulation                                     ###
###########################################################################

def draw(threshold):
    ### Helper function
    ### Returns a random real number between 0 and 1.
    def __draw__():
        return(random.random())
    ###
    draw_val = __draw__()
    if (draw_val <= threshold):
        draw_val = __draw__()
    ###
    return(draw_val)



# %% ######################################################################
###     2.1.        Game Simulation                                     ###
###########################################################################

for i in range(num_game):
    p1_val = draw(p1_threshold)
    for k in p2_strategy.keys():
        p2_val = draw(p2_strategy[k]["threshold"])
        if (p1_val > p2_val):
            p2_strategy[k]["wins_p1"] += 1
        else:
            p2_strategy[k]["wins_p2"] += 1



# %% ######################################################################
###     2.2.        Results                                             ###
###########################################################################

var = 0.5 * (1 - 0.5)
sum_var = num_game * var
std = sum_var ** 0.5
expected = num_game * 0.5
print("\n", " " * 4,
    f"Player 1 has a threshold of {p1_threshold}.",
    "\n", " " * 4,
    f"Simulate {num_game:,} games against each of player 2's strategies.",
    "\n",
    sep = "")
for k in p2_strategy.keys():
    z_score = (p2_strategy[k]['wins_p1'] - expected) / std
    p_val = scipy.stats.norm.cdf(z_score)
    print(" " * 4,
        f"Against {k} strategy:",
        sep = "")
    print(" " * 4,
        f"Win  : {round(100 * p2_strategy[k]['wins_p1'] / num_game, 4)} %",
        sep = "")
    print(" " * 4,
        f"Lose : {round(100 * p2_strategy[k]['wins_p2'] / num_game, 4)} %",
        sep = "")
    print(" " * 4,
        f"Z-score : {round(z_score, 2)}",
        sep = "")
    print(" " * 4,
        f"Probability of having a winning strategy : {round(100 * p_val, 2)} %",
        "\n",
        sep = "")



###########################################################################



# %% ######################################################################
###     3.0.        Explanation - Function                              ###
###########################################################################

### Set threshold as variable p.

### Case 1 : draw under p, draw under p
###     Probability : p * p
###     Conditional Value : (0 + p) / 2

### Case 2 : draw under p, draw over p
###     Probability : p * (1 - p)
###     Conditional Value : (p + 1) / 2

### Case 3 : draw over p
###     Probability : 1 - p
###     Conditional Value : (p + 1) / 2

### Derive f(p), the expected draw value given a threshold p.
### f(p) =
###     (p * p)         *   ((0 + p) / 2) +
###     (p * (1 - p))   *   ((p + 1) / 2) +
###     (1 - p)         *   ((p + 1) / 2)
### = (p^3 / 2) + ((p - p^3) / 2) + ((1 - p^2) / 2)
### = - (p^2 - p - 1) / 2



# %% ######################################################################
###     3.1.        Explanation - Optimization                          ###
###########################################################################

### f(p) has roots at (1 ± √(5)) / 2
### f(p) is maximized at (p, f(p)) = (1/2 = 0.5, 5/8 = 0.625)



# %% ######################################################################
###     3.2.        Explanation - Suboptimization                       ###
###########################################################################

### f(5/8) = 79/128 = 0.6171875

### Setting p = 0.5 maximizes the expected draw value at 0.625.
### Setting p = 0.625 lowers the expected draw value,
###     but maximizes the win rate assuming the opponent plays optimally.

### The goal is to maximixe win rate, not expected draw value.
### The two are correlated, but not substitutable.

### Extended exercise : how would this strategy change with more players?
