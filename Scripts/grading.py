import glob
import logging
import shutil
import subprocess
import sys
import os
import pandas as pd
from pathlib import Path
import re

original_test_dirs_path = "/mnt/d/TA/COMP 348/Grading/GRADING/test_folders"
STUDENT_CSV = "/mnt/d/TA/COMP 348/Grading/GRADING/students.csv"

logging.basicConfig(level=logging.INFO)


def load_dataframe_students(student_csv=STUDENT_CSV):
    return pd.read_csv(STUDENT_CSV)


def make_grading_dir(grading_dir_path):
    if not os.path.exists(grading_dir_path):
        os.makedirs(grading_dir_path)


def copy_src_code(src_code_path, grading_dir_path):
    src_code_file_paths = [src_file_path.lower() for src_file_path in glob.glob(os.path.join(src_code_path, "*"))
                           if (".c" in src_file_path.lower()) or (".h" in src_file_path.lower()) or (
                                   'readme.txt' in src_file_path.lower())]

    for src_code_file_path in src_code_file_paths:
        src_code_file_name = src_code_file_path.split("/")[-1]
        new_path = os.path.join(grading_dir_path, src_code_file_name)
        shutil.copy(src_code_file_path, new_path)
        logging.info(f"Copied src file: {src_code_file_name}")


def set_up_test_dirs(grading_dir_path, original_test_dirs_path=original_test_dirs_path):
    # remove if test directories are already present
    shutil.rmtree(os.path.join(grading_dir_path, "test_dirs"), ignore_errors=True)
    shutil.copytree(original_test_dirs_path, os.path.join(grading_dir_path, "test_dirs"))


def compile_code(grading_dir_path):
    """gcc -Wall -g -gdwarf-4 report.c text.c traversal.c replace.c"""
    command = ["gcc", "-Wall", "-g", "-gdwarf-4"]
    src_c_files = [file for file in glob.glob(os.path.join(grading_dir_path, '*')) if ".c" in file]
    command += src_c_files
    command += ["-o", f"{os.path.join(grading_dir_path, 'a.out')}"]
    logging.debug(f"Command: {command}")

    # https://www.dataquest.io/blog/python-subprocess/
    result = subprocess.run(command, capture_output=True, text=True)
    logging.info(f"Compiling: {'SUCCESSFUL' if result.returncode == 0 else 'FAILED'}")
    compilation_report_path = os.path.join(grading_dir_path,
                                           f"{'SUCCESSFUL' if result.returncode == 0 else 'FAILED'}_compilation.txt")
    with open(compilation_report_path, "w") as f:
        f.write(f"COMPILATION RETURN CODE: {result.returncode}\n\n")
        f.write(f"COMPILATION STDOUT: {result.stdout}\n\n")
        f.write(f"COMPILATION STDERR: {result.stderr}\n\n")
    if result.returncode != 0:
        logging.critical("COMPILATION FAILED, cannot proceed with grading")
        sys.exit(-1)


def run_tests(grading_dir_path):
    for test_dir_path in glob.glob(os.path.join(grading_dir_path, "test_dirs", "*")):
        run_test(grading_dir_path, test_dir_path)


def run_test(grading_dir_path, test_dir_path):
    # copy the executable from grading to test_dir\
    test_name = test_dir_path.split('/')[-1]
    executable_path = os.path.join(grading_dir_path, "a.out")
    shutil.copy(executable_path, os.path.join(test_dir_path, "a.out"))  # will overwrite
    logging.info(f"Copied executable to [...]/{test_name}")

    # run the executable
    command = ["./a.out", "apple"]
    result = subprocess.run(command, cwd=test_dir_path, capture_output=True, text=True)

    logging.info(f"{test_name}: {'ran without errors' if result.returncode == 0 else 'ERROR while running'}")

    test_report_path = os.path.join(test_dir_path, test_name + '.txt')
    with open(test_report_path, "w") as f:
        f.write(f"TEST RETURN CODE: {result.returncode}\n\n")
        f.write(f"TEST STDOUT: {result.stdout}\n\n")
        f.write(f"TEST STDERR: {result.stderr}\n\n")
    logging.info(f"{test_name}: Test report saved")

    # Check if the program updated the test files correctly
    all_modified_test_files = [str(path.absolute()) for path in Path(test_dir_path).rglob('*')]
    # remove a.out, DS_Store and test report from any previous run
    all_modified_test_files = [_ for _ in all_modified_test_files if
                               "a.out" not in _ and f"{test_name}.txt" not in _ and 'DS_Store' not in _ and ".txt" in _]
    all_original_test_files = [str(path.absolute()) for path in
                               Path(os.path.join(original_test_dirs_path, test_name)).rglob("*")]
    all_original_test_files = [_ for _ in all_original_test_files if 'DS_Store' not in _ and ".txt" in _]

    logging.info(f"For test directory: {test_name}")
    for modified_test_file in all_modified_test_files:
        for original_test_file in all_original_test_files:
            if modified_test_file.split("/")[-1] == original_test_file.split("/")[-1]:
                logging.info(f'Testing: {"/".join(original_test_file.split("/")[8:])}')
                check_occurrences_of_keyword(original_test_file, modified_test_file, 'apple')


def check_occurrences_of_keyword(original_file, modified_file, keyword='apple'):
    original_words = []
    modified_words = []
    # split on any whitespace to tokenize the files
    # we consider any word which has the keyword in it, for eg, AppLesauce is a valid word to be tested
    with open(original_file, "r") as f:
        original_words = [word for word in f.read().split() if keyword in word.lower()]
    with open(modified_file, "r") as f:
        modified_words = [word for word in f.read().split() if keyword in word.lower()]
    correct_updates = 0
    missed_updates = 0
    for original_word, modified_word in zip(original_words, modified_words):
        # we match original_word to modified_word just to check if correct word has been updated
        starting_indices_in_original_word = [m.start() for m in
                                             re.finditer(keyword, original_word, flags=re.IGNORECASE)]
        starting_indices_in_modified_word = [m.start() for m in
                                             re.finditer(keyword, modified_word, flags=re.IGNORECASE)]
        # starting_indices in both should match
        if starting_indices_in_original_word == starting_indices_in_modified_word:
            for starting_index in starting_indices_in_modified_word:
                # Note that no. of updates does not refer to just one word, for eg, apPLEapple -> APPLEAPPLE requires 2 updates
                if modified_word[starting_index:starting_index + len(keyword)].isupper():
                    correct_updates += 1
                else:
                    missed_updates += 1
                    logging.debug(
                        f"ERROR: missed update for {modified_word[starting_index:starting_index + len(keyword)]}")
        else:
            logging.error("ERROR: starting indices of modified keywords do not match")
    logging.info(f"{correct_updates} correct updates, {missed_updates} missed updates, for {len(original_words)} words")


def check_memory_leaks(grading_dir_path):
    """valgrind --leak-check= full ./a.out apple"""
    command = ["valgrind", "--leak-check=full", "./a.out", "apple"]
    result = subprocess.run(command, capture_output=True, text=True, cwd=grading_dir_path)
    mem_leaks = True
    if "ERROR SUMMARY: 0 errors" in result.stderr:
        mem_leaks = False
    logging.info(f"Valgrind: memcheck: {'NO ERRORS' if not mem_leaks else 'ERRORS'}")
    memcheck_report_path = os.path.join(grading_dir_path,
                                        f"{'NO_ERRORS' if not mem_leaks else 'ERRORS'}_memcheck.txt")
    with open(memcheck_report_path, "w") as f:
        f.write(f"MEMCHECK RETURN CODE: {result.returncode}\n\n")
        f.write(f"MEMCHECK STDOUT: {result.stdout}\n\n")
        f.write(f"MEMCHECK STDERR: {result.stderr}\n\n")


def main():
    # src_code_path = "/mnt/d/TA/COMP 348/Grading/SOLUTION_"
    src_code_path = sys.argv[1]
    if not src_code_path:
        print("SRC PATH not specified")
        sys.exit()
    grading_dir_path = "/".join(src_code_path.split("/") + ["grading"])

    # Display the student name
    logging.info(f"Testing student: {src_code_path.split('/')[-1].split('_')[0]}")

    # Create the grading directory
    make_grading_dir(grading_dir_path)
    logging.info(f"Created grading directory: {grading_dir_path}")

    # copy source files to "grading" directory
    logging.info("Copying source files to the grading directory")
    copy_src_code(src_code_path, grading_dir_path)

    # copy test directories into "grading" directory
    logging.info("Setting up test directories")
    set_up_test_dirs(grading_dir_path)

    # compile code and save output
    logging.info("Compiling code")
    compile_code(grading_dir_path)

    # copy executable into grading/test_dirs/{T1,T2,T3} and run and save output
    run_tests(grading_dir_path)

    # run valgrind and save output
    check_memory_leaks(grading_dir_path)


if __name__ == "__main__":
    main()
