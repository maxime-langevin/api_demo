import logging
import os
import re
import sys
import time
import warnings
from functools import wraps
from logging.handlers import RotatingFileHandler

import pandas as pd
import yaml
from unidecode import unidecode

warnings.filterwarnings("ignore")


class Timer:
    def __init__(self):
        self.laps = {}

    def add_lap(self, name: str, time: float):
        self.laps[name] = time

    def print_lap(self, name):
        print(f"Function {name}: \t{self.laps[name]:.2f} seconds")

    def print_total(self):
        total_time = sum([time for _, time in self.laps.items()])
        print(f"Total execution time: \t\t{total_time:.2f} seconds \n")

    def timeit(self, func):
        @wraps(func)
        def timeit_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            total_time = end_time - start_time
            self.add_lap(func.__name__, total_time)
            return result

        return timeit_wrapper


def configure_logger():
    # Create the "log_files" directory if it doesn't exist
    log_dir = "log_files"
    os.makedirs(log_dir, exist_ok=True)

    # Create a logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a file handler with rotating file support in the "log_files" directory
    log_file_path = os.path.join(log_dir, "app.log")
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)

    # Create a formatter and set the formatter for the handler
    formatter = logging.Formatter(
        "[%(asctime)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler)

    return logger


logger = configure_logger()


def wrap(pre, post):
    """Wrapper"""

    def decorate(func):
        """Decorator"""

        def call(*args, **kwargs):
            """Actual wrapping"""
            pre(func)
            result = func(*args, **kwargs)
            post(func)
            return result

        return call

    return decorate


def entering(func):
    """Pre function logging"""
    logger.debug("Entered %s", func.__name__)
    logger.info(func.__doc__)


def exiting(func):
    """Post function logging"""
    logger.debug("Exited  %s", func.__name__)


def print_help():
    """Print help text and exit"""
    print(
        """
    Deepia PDF Plugin
    Usage: main.py [ARGS] [OPTIONS]

    Arguments:
      PDF_Path           pdfs/example_alphabio.pdf

    Options:
      Test           Specific test(s) to print (Hématies Hémoglobine...)
      All_Units      Print other units if available (True/False)
      -h, --help     Print help text and exit
    """
    )
    sys.exit(1)


@wrap(entering, exiting)
def result_search(pdf_lines):
    """returns all the potential matches for medical analysis result in a pdf file, using regex"""

    # simplify the regex for numbers
    sign = r"(?:[+-<>]?)"
    decimal_numbers = r"(?:\d+(\s\d*)*(,\d*)?|\d+(\,\d*)?)"
    special_cases = r"(?:inf(\.)?)"
    neg_or_pos = r"(?:n[eé]gatif\.?)|(positif\.?)"

    # define regex for categories: word, number, scientific unit, and separators
    word = r"\.?[^\d]+\.?"
    number = sign + "(" + decimal_numbers + "|" + special_cases + "|" + neg_or_pos + ")"
    unit = r"\.?[^\s()]+\.?"
    no_alphanum = r"[^A-Za-z0-9+-<>]*"
    # build regex to match pattern found in pdf files for medical analysis results
    pattern = (
        r"(?P<displayed_name>"
        + word
        + ")(\s)+(?P<value>"
        + number
        + ")(\s)+((?P<unit>"
        + unit
        + ")(\s)+("
        + no_alphanum
        + ")?((?P<low_reference>"
        + number
        + ")("
        + word
        + ")?(?P<high_reference>"
        + number
        + ")?)?)?"
    )
    pattern2 = (
        r"(?P<displayed_name>"
        + word
        + ")(\s)+(?P<value>"
        + number
        + ")(\s)+(?P<unit>"
        + unit
        + ")(\s)+.*soit(\s)+(?P<value2>"
        + number
        + ")(\s)+((?P<unit2>"
        + unit
        + ")(\s)+("
        + no_alphanum
        + ")?((?P<low_reference>"
        + number
        + ")("
        + word
        + ")?(?P<high_reference>"
        + number
        + ")?)?)?"
    )

    # match the regex to each line of the pdf to detect for potential results
    result = []
    for line in pdf_lines:
        # try all four patterns
        match = re.match(pattern, line, re.IGNORECASE)
        match2 = re.match(pattern2, line, re.IGNORECASE)
        # add potential matches as dicts to the result list
        if match2:
            result.append(
                {
                    "displayed_name": match2.group("displayed_name"),
                    "value": match2.group("value"),
                    "unit": match2.group("unit"),
                    "low_reference": "nan",
                    "high_reference": "nan",
                }
            )
            result.append(
                {
                    "displayed_name": match2.group("displayed_name"),
                    "value": match2.group("value2"),
                    "unit": match2.group("unit2"),
                    "low_reference": match2.group("low_reference"),
                    "high_reference": match2.group("high_reference"),
                }
            )
        elif match:
            result.append(
                {
                    "displayed_name": match.group("displayed_name"),
                    "value": match.group("value"),
                    "unit": match.group("unit"),
                    "low_reference": match.group("low_reference"),
                    "high_reference": match.group("high_reference"),
                }
            )
    # rebuild output format for special cases
    for line in result:
        try:
            if "<" in line["low_reference"]:
                line["high_reference"] = line["low_reference"].replace("<", "")
                line["low_reference"] = None
            elif "<" in line["high_reference"]:
                line["high_reference"] = line["high_reference"].replace("<", "")
                line["low_reference"] = None
            elif ">" in line["low_reference"]:
                line["low_reference"] = line["low_reference"].replace(">", "")
                line["high_reference"] = None
            elif ">" in line["high_reference"]:
                line["low_reference"] = line["high_reference"].replace(">", "")
                line["high_reference"] = None
        except:
            pass
        # convert numbers to floats
        try:
            line["value"] = float(line["value"].replace(",", "."))
        except:
            pass
        try:
            line["low_reference"] = float(line["low_reference"].replace(",", "."))
        except:
            pass
        try:
            line["high_reference"] = float(line["high_reference"].replace(",", "."))
        except:
            pass

    return result


def levenshtein_distance_prop(str1, str2):
    """returns the levenshtein distance between two strings, as a proportion of the string length"""

    # get lengths from both string
    len_str1 = len(str1) + 1
    len_str2 = len(str2) + 1
    # build the comparision matrix
    matrix = [[0] * len_str2 for _ in range(len_str1)]
    for i in range(len_str1):
        matrix[i][0] = i
    for j in range(len_str2):
        matrix[0][j] = j
    for i in range(1, len_str1):
        for j in range(1, len_str2):
            cost = 0 if str1[i - 1] == str2[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,  # deletion
                matrix[i][j - 1] + 1,  # insertion
                matrix[i - 1][j - 1] + cost,  # substitution
            )

    levenshtein_distance = matrix[-1][-1]
    # return the distance as a proportion of the strings' lengths
    return levenshtein_distance / (max(len(str1), len(str2)))


def give_test_result(test_name, results_list):
    """returns the result from a medical test given a result list computed from a pdf"""

    # find the match in the result that correspond to the test's name
    results = [
        elem
        for elem in results_list
        if unidecode(test_name.lower()) in unidecode(elem["displayed_name"].lower())
        or levenshtein_distance_prop(
            unidecode(test_name.lower()), unidecode(elem["displayed_name"].lower())
        )
        <= 0.05
    ]
    # reshape the output
    # for i in range(len(results)):
    # results[i] = {key: results[i][key] for key in results[i] if key != "displayed_name"}

    return results


def read_yaml(path_result):
    """return a yaml file as a dictionary"""

    with open(path_result, "r") as file:
        result = yaml.safe_load(file)

    return result


def accuracy(pdf_lines, path_result, search_type="block"):
    """
    Returns the accuracy between a result from a pdf file analysis and its corresponding real
    result yaml file
    """
    # pdf_lines is the result of read_pdf_text, read_pdf_text_using_img, or read_pdf_block
    # read the text in the pdf given the chosen method
    # search medical analysis results in the text from the pdf
    search_result = result_search(pdf_lines)
    # read real results file
    real_result = read_yaml(path_result)["data"]
    real_result = pd.DataFrame(real_result)
    try:
        real_result = real_result.drop(columns="unit_alt")
    except:
        pass
    # replace wrongly encoded characters in the yaml
    real_result = real_result.applymap(
        lambda x: (
            x.replace("Ã©", "é").replace("Ã¨", "è").replace("Â", "") if isinstance(x, str) else x
        )
    )
    # count the number of identical result between the detection and the real results
    counter = 0
    for test_name in real_result["displayed_name"]:
        # find the corresponding outputs
        matching_results = give_test_result(test_name, search_result)
        if len(matching_results) > 0:
            counter += 1
            prev_counter = counter
            for matching_result in matching_results:
                for key in matching_result:
                    if (
                        real_result[key][real_result["displayed_name"] == test_name].values[0]
                        == matching_result[key]
                    ):
                        counter += 1
                    elif pd.isnull(
                        real_result[key][real_result["displayed_name"] == test_name].values[0]
                    ) and pd.isnull(matching_result[key]):
                        counter += 1
                    else:
                        pass
            # print the result for test where each fields were not detected
            if prev_counter + 4 > counter:
                print(test_name, key, matching_result)

    return counter / real_result.size
