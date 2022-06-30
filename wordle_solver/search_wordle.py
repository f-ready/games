# %% ######################################################################
###                                                                     ###
###                          Table of Contents                          ###
###                                                                     ###
###     0.          Dependent Libraries                                 ###
###     1.          Variable Initialization                             ###
###     2.0.        Class - Initialization                              ###
###     2.1.        Class - Clues (Private Data Structure)              ###
###     1.2.    Class - Words (Private Data Structure)                  ###
###     1.3.    Class - Search (Private Data Structure)                 ###
###     1.4.    Class - Play (Public Data Access)                       ###
###     2.0.    Search - Instance                                       ###
###                                                                     ###
###########################################################################
###                                                                     ###
###     A "solver" for the game Wordle.                                 ###
###     Searches for the next best guess.                               ###
###     The best guess is defined as the guess that would, on average,  ###
###         reduce the number of possible answers the most.             ###
###                                                                     ###
###########################################################################



# %% ######################################################################
###     0.          Dependent Libraries                                 ###
###########################################################################

import concurrent.futures, gc, time
import itertools, pandas as pd, re, string
import os



# %% ######################################################################
###     1.          Variable Initialization                             ###
###########################################################################

wrk_dir = os.getcwd()



# %% ######################################################################
###     2.0.        Class - Initialization                              ###
###########################################################################

class wordle_guesser:
    ###
    __num_chars__ = 0
    __colours__ = ""
    __colour_vals__ = {}
    __words_all__ = []
    __words_possible__ = []
    __clues__ = {}
    __solution_simulation__ = {}
    __guess_metrics__ = {}
    __best_guess__ = ""
    ###
    def __init__(self, num_chars = 5):
        ### Number of characters in word.
        assert num_chars > 0, "Specify positive word length"
        self.__num_chars__ = num_chars
        ###
        ### Order in which to evaluate response.
        self.__colours__ = "gyb"
        ###
        ### Quantify the colour response.
        self.__colour_vals__ = {
            "g" : None, # Replace with index of character
            "y" : -1,
            "b" : -2,
            "unknown" : -3}
        ###
        ### List of all words of appropriate length.
        self.__words_all__ = pd.read_csv(
            os.path.join(
                wrk_dir,
                f"words_letters_{self.__num_chars__}.csv"),
            header = None) \
            [0].values.tolist()
        ###
        ### List of all words that are possible solutions.
        self.__words_possible__ = self.__words_all__
        ###
        ### Current clue status.
        ### Data structure was built to accomodate the scenario where
        ###     the solution and/or guess have duplicate letters.
        self.__clues__ = dict.fromkeys(
            string.ascii_lowercase,
            [self.__colour_vals__["unknown"]])
        ###
        ### Data structure storing the potential next clue status.
        self.__solution_simulation__ = {}
        ###
        ### Numeric evaluation of the current solution simulation.
        self.__guess_metrics__ = {}
        ###
        ### The currrent next best guess.
        ### The first best guess is cached as an constant on the
        ###     constant prior of no information.
        self.__best_guess__ = ""
        self.__calc_best_guess__()
        print(f"Best guess is {self.__best_guess__}.")
        ###
        return



###########################################################################
###     2.1.        Class - Clues (Private Data Structure)              ###
###########################################################################



    def __clues_std_response__(self, input_1, input_2 = ""):
        ### Standardize input_1 as a string.
        if (isinstance(input_1, str)):
            pass
        elif (isinstance(input_1, list)):
            input_1 = "".join(input_1)
        else:
            assert True, f"Unknown input_1 type {type(input_1).__name__}."
        ###
        ### Standardize input_2 as a string.
        if (isinstance(input_2, str)):
            pass
        elif (isinstance(input_2, list)):
            input_2 = "".join(input_2)
        else:
            assert True, f"Unknown input_2 type {type(input_2).__name__}."
        ###
        ### Remove potential white space.
        input_1 = re.sub("\s", "", input_1.lower())
        input_2 = re.sub("\s", "", input_2.lower())
        ###



        response = input_1 + input_2
        response = re.sub("\s", "", response.lower())
        assert len(response) == self.__i__ * 2, \
            f"{self.__i__ * 2} characters not specified"
        ltr = response[:self.__i__]
        clr = response[self.__i__:]
        assert re.search(fr"^[{self.__colours__}]{{{self.__i__}}}$", clr) \
                is not None, \
            f"Invalid response : {response} - {ltr} : {clr}."
        d = {}
        for colour in self.__colours__:
            idxs = [x.start() for x in re.finditer(colour, clr)]
            for idx in idxs:
                ltr_i = ltr[idx]
                colour_val = self.__colour_vals__[colour] or idx
                if (ltr_i not in d.keys()):
                    d[ltr_i] = []
                d[ltr_i].append(colour_val)
        return(d)

    def __clues_get__(self, ignore_keys, clue_env = None):
        clue_env = clue_env or self.__clues__
        ignore_vals = [self.__colour_vals__[k] for k in ignore_keys]
        clues_relevant = {}
        for k in string.ascii_lowercase:
            v_relevant = [v
                for v in clue_env[k]
                if (v not in ignore_vals)]
            if (len(v_relevant) == 0):
                continue
            clues_relevant[k] = v_relevant
        return(clues_relevant)

    def __clues_get_known__(self, clue_env = None):
        clue_env = clue_env or self.__clues__
        return(self.__clues_get__(["unknown"], clue_env = clue_env))

    def __clues_get_unknown__(self, clue_env = None):
        clue_env = clue_env or self.__clues__
        clues_relevant = {}
        for k in string.ascii_lowercase:
            if (clue_env[k][0] == self.__colour_vals__["unknown"]):
                clues_relevant[k] = clue_env[k]
        return(clues_relevant)

    def __clues_sort__(self, lst):
        ### Only for reference. Sorts values.
        ### Semi-positives come first in ascending order.
        ### Negatives come second in descending order
        ### ex : [0, 1, 2, 3, 4, -1, -2, -3]
        return(sorted(lst, key = lambda v :
            - self.__i__ if (v == 0)
            else - 1 / v if (v > 0)
            else abs(v)))

    def __clues_merge_list__(self, lst_1, lst_2):
        lst_g_1 = [v for v in lst_1 if (v >= 0)]
        lst_g_2 = [v for v in lst_2 if (v >= 0)]
        lst_g = list(set(lst_g_1) | set(lst_g_2))
        num_known_1 = len(lst_g_1) + \
            lst_1.count(self.__colour_vals__["y"])
        num_known_2 = len(lst_g_2) + \
            lst_2.count(self.__colour_vals__["y"])
        num_known = max(num_known_1, num_known_2)
        lst_y = [self.__colour_vals__["y"]] * (num_known - len(lst_g))
        if ((lst_1[-1] == self.__colour_vals__["b"]) or
            (lst_2[-1] == self.__colour_vals__["b"])):
            lst_b = [self.__colour_vals__["b"]]
        else:
            lst_b = [self.__colour_vals__["unknown"]]
        return(lst_g + lst_y + lst_b)

    def __clues_merge_dict__(self, dct_1, dct_2):
        dct_1 = dct_1.copy()
        for k in dct_2.keys():
            if (dct_2[k][0] == self.__colour_vals__["b"]):
                dct_1[k] = [self.__colour_vals__["b"]]
            else:
                dct_1[k] = self.__clues_merge_list__(
                    dct_1[k], dct_2[k])
        return(dct_1)

    def __clues_update__(self, input_1, input_2 = "", clue_env = None):
        clue_env = clue_env or self.__clues__
        response = self.__clues_std_response__(input_1, input_2)
        assert response is not None, ""
        clue_env = self.__clues_merge_dict__(clue_env, response)
        return(clue_env)

    def __clues_decipher__(self, clue_env = None):
        clue_env = clue_env or self.__clues__
        ltrs_known = self.__clues_get_known__(clue_env = clue_env)
        ltrs_g = ["."] * self.__i__
        ltrs_y = []
        ltrs_b = []
        ltrs_u = []
        for k in string.ascii_lowercase:
            for v in clue_env[k]:
                if (v == self.__colour_vals__["unknown"]):
                    ltrs_u.append(k)
                elif (v == self.__colour_vals__["b"]):
                    ltrs_b.append(k)
                elif (v == self.__colour_vals__["y"]):
                    ltrs_y.append(k)
                else:
                    ltrs_g[v] = k
        return("".join(ltrs_g), "".join(ltrs_y),
                "".join(ltrs_b), "".join(ltrs_u))

    def __clues_summary__(self, show_words):
        ltrs_g, ltrs_y, ltrs_b, ltrs_u = self.__clues_decipher__()
        ltrs_y = "".join(sorted(ltrs_y))
        ltrs_u = "".join(sorted(ltrs_u))
        ret_value = None
        if ("." not in ltrs_g):
            print(f"You 100% dumbass, you have the word.")
            print(f"The word is {ltrs_g}.")
        elif (ltrs_g.count(".") == len(ltrs_y)):
            print(f"You  99% dumbass, you have all the letters.")
            print(f"The word is {ltrs_g} with letters {ltrs_y}.")
        else:
            print(f"The word is {ltrs_g} with letters {ltrs_y}.")
            print(f"{len(ltrs_u)} possible letters are {ltrs_u}.")
            print(f"{len(self.__words_possible__)} possible words.")
            if (show_words or (len(self.__words_possible__) <= 50)):
                print(self.__words_possible__)
        return



###########################################################################
###     1.2.    Class - Words (Private Data Structure)                  ###
###########################################################################

    def __word_check__(self, word, clue_env = None):
        word = word.lower()
        clue_env = clue_env or self.__clues__
        ltrs_g, ltrs_y, ltrs_b, ltrs_u = \
            self.__clues_decipher__(clue_env = clue_env)
        if (re.match(ltrs_g, word) is None):
            return(False)
        col_u = self.__colour_vals__["unknown"]
        col_b = self.__colour_vals__["b"]
        for k in string.ascii_lowercase:
            clue_first = clue_env[k][0]
            if (clue_first == col_u):
                continue
            elif (clue_first == col_b):
                if (k in word):
                    return(False)
            else:
                if (clue_env[k][-1] == col_u):
                    if (word.count(k) < (len(clue_env[k]) - 1)):
                        return(False)
                else:
                    if (word.count(k) != (len(clue_env[k]) - 1)):
                        return(False)
        return(True)

    def __words_update__(self, clue_env = None, word_env = None):
        clue_env = clue_env or self.__clues__
        word_env = word_env or self.__words_possible__
        new_words = [w for w in word_env
                        if (self.__word_check__(w, clue_env))]
        return(new_words)



###########################################################################
###     1.3.    Class - Search (Private Data Structure)                 ###
###########################################################################

    def __create_clue__(self, answr, guess):
        d = {}
        for k in set(guess):
            if (k not in answr):
                # d[k] = [self.__colour_vals__["b"]]
                d[k] = [-2]
                continue
            d[k] = []
            idx_answr = [x.start() for x in re.finditer(k, answr)]
            idx_guess = [x.start() for x in re.finditer(k, guess)]
            for idx in idx_guess:
                if (idx in idx_answr):
                    d[k].append(idx)
            cnt_answr = len(idx_answr)
            cnt_guess = len(idx_guess)
            num_to_append = min(cnt_guess, cnt_answr) - len(d[k])
            # d[k].append([self.__colour_vals__["y"]] * num_to_append)
            d[k].extend([-1] * num_to_append)
            num_to_append = cnt_guess - cnt_answr
            # d[k].append([self.__colour_vals__["b"]] * num_to_append)
            d[k].extend([-2] * num_to_append)
        return(d)

    def __simulate_answr__(self, answr):
        if (answr not in self.__solution_simulation__.keys()):
            self.__solution_simulation__[answr] = {}
        iter_words = self.__solution_simulation__[answr].keys()
        if (len(iter_words) == 0):
            iter_words = self.__words_possible__
            for guess in iter_words:
                self.__solution_simulation__[answr][guess] = []
        else:
            for guess in set(iter_words) - set(self.__words_possible__):
                del self.__solution_simulation__[answr][guess]
        for guess in self.__words_possible__:
            simulate_word = self.__solution_simulation__[answr][guess]
            if (len(simulate_word) == 0):
                simulate_word = self.__words_possible__
            simulate_clue = self.__create_clue__(answr, guess)
            simulate_info = self.__clues_merge_dict__(
                self.__clues__, simulate_clue)
            new_words = self.__words_update__(
                clue_env = simulate_info,
                word_env = simulate_word)
            self.__solution_simulation__[answr][guess] = new_words
        return

    def __simulate_answrs__(self):
        iter_words = self.__solution_simulation__.keys()
        if (len(iter_words) == 0):
            iter_words = self.__words_possible__
            for answr in iter_words:
                self.__solution_simulation__[answr] = {}
        else:
            for answr in set(iter_words) - set(self.__words_possible__):
                del self.__solution_simulation__[answr]
        for answr in self.__words_possible__:
            self.__simulate_answr__(answr)
        return

    def __simulate_evaluate__(self):
        self.__guess_metric__ = {}
        for guess in self.__words_possible__:
            guess_metric = []
            for answr in self.__words_possible__:
                guess_metric.append(
                    len(self.__solution_simulation__[answr][guess]))
            self.__guess_metric__[guess] = \
                round(sum(guess_metric) / len(guess_metric), 2)
        guess_order = sorted(
            self.__guess_metric__.keys(),
            key = lambda k : self.__guess_metric__[k])
        self.__best_guess__ = guess_order[0]
        return

    def __cnt_ltrs__(self):
        ltr_cnt = {}
        for k in string.ascii_lowercase:
            if (self.__clues__[k][0] != self.__colour_vals__["unknown"]):
                continue
            ltr_cnt[k] = len([w for w in self.__words_possible__
                                if (k in w)])
        ltrs_sorted = sorted(
            ltr_cnt.keys(),
            key = lambda k : ltr_cnt[k],
            reverse = True)
        for com in itertools.combinations(ltrs_sorted, 5):
            use_rgx = "[" + "".join(com) + "]"
            words_good = [w for w in self.__words_all__
                if ((len(set(w)) == self.__i__) and
                    (len(re.findall(use_rgx, w)) == self.__i__))]
            if (len(words_good) != 0):
                self.__best_guess__ = words_good[0]
                break
        return

    def __calc_best_guess__(self):
        if (len(self.__words_possible__) >= 150):
            self.__cnt_ltrs__()
        else:
            self.__simulate_answrs__()
            self.__simulate_evaluate__()
        return



###########################################################################
###     1.4.    Class - Play (Public Data Access)                       ###
###########################################################################

    def play(self, input_1, input_2 = "", show_words = False):
        self.__clues__ = self.__clues_update__(input_1, input_2)
        self.__words_possible__ = self.__words_update__()
        ret_value = self.__clues_summary__(show_words = show_words)
        self.__calc_best_guess__()
        print(f"\nBest guess is {self.__best_guess__}.")
        return(ret_value)



# %% ######################################################################
###     2.0.    Search - Instance                                       ###
###########################################################################

search = solve_wordle(5)

# %% ######################################################################

t0 = time.time()
x = search.play("aeros", "yyybb")
t1 = time.time()
print(t1 - t0)

# %% ######################################################################

t0 = time.time()
x = search.play("dicty", "bbbbb")
t1 = time.time()
print(t1 - t0)

# %% ######################################################################

t0 = time.time()
x = search.play("rager", "yybyb")
t1 = time.time()
print(t1 - t0)

# %% ######################################################################

t0 = time.time()
x = search.play("marle", "yyybg")
t1 = time.time()
print(t1 - t0)

# %% ######################################################################

t0 = time.time()
x = search.play("brake", "bggbg")
t1 = time.time()
print(t1 - t0)

# %% ######################################################################
###     z.  Temporary                                                   ###
###########################################################################

search.__solution_simulation__

search.__guess_metric__["brake"]
search.__guess_metric__["marle"]







































###########################################################################
