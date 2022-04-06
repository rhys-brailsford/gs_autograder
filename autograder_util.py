#!/usr/bin/python3.8
import json
import os
import sys
from datetime import datetime, timedelta
import math
import subprocess
from pytz import timezone
import shutil


"""
============
Gradescope autograder script
Feb 2022

by Rhys Brailford (a1667692)
School of Computer Science
University of Adelaide
============

To use:
    1. The script expects to be run in the gradescope environment and therefore you will need to
        emulate it. Check below for file structure requirements.
    2. Create a Question object for each question (e.g. "1-1", "1-2", "3-5")
        and store in list  "questions".
    3. Each question can use optional CompileTest objects that defined the required files for
        each compile test. If extra files are required that aren't used for compilation directly (header files,
		plan.txt, solution.txt, etc.), a separate field in the Question class can be used: Question.extra_files.
		These files get checked for FilesPresent checks but not used in compiling.
	4. Points are broken into 3 types: FilesPresent (only gives points if all required files are present),
		CompileTest for successful compilation, and functionality test defined by output files.
    5. If functionality tests are needed, specify the index which CompileTest in Question.compile_tests
        to use for compiling the test driver by using Question.tester_idx.
    6. Functionality tests are defined by output files in ./source/ directory.
        output-2-3-01 refers to Question 2-3, test 01. An output file is required per functionality test.
	7. Functionality tests are usually defined using a test driver in ./source/ with the name "test-1-1.cpp"
		for question 1-1. Cmd line arguments can be put in args-1-1-00 (again, for Q1-1, Test 00), stdin inputs
		in input-1-1-00, and expected output in output-1-1-00.
    8. To run, simply call ./run_autograder in this script directory, no input needed as test information
        is either embedded in this script or in ./source/ or ./submission/ directories.
    9. Results are written to results/resuls.json which contains a score and a list of tests performed.
        Tests are consolidated by question (e.g. test will contain file/compile tests as well as functionality tests).

File Structure:
- ./run_autograder : This script
- ./submission : All submitted files
- ./source : All source files that get uploaded to gradescope with this script. Examples:
    - ./source/args-I-J-XY : <optional> contains cmd line arguments for Question I-J, Test XY
    - ./source/input-I-J-XY : <optional> contains input (via stdin redirection) for QI-J-XY as above
    - ./source/output-I-J-XY : <optional> contains expected output that gets diff'd for functionality test
    - ./source/test-I-J.cpp : <optional> contains test driver for Question I-J.
- ./submission_metadata.json : meta data for current submission,
    contains submitted time/duedate/max grade/previous submissions, etc.
- ./results/results.json : contains results file that gradescope reads for their output
- ./setup.sh : contains setup commands. Python module installations need to be done using:
            "python3.8 -m pip install X", where X is the module/command. This script depends on pytz.

Example Use case:

c_tests = []
# Create compile test for supplied main file. Successful compile gives 2 points.
# submitted_files contains list of required files submitted by student.
# provided_files contains list of required files supplied by testing harness.
main_compile = CompileTest(submitted_files = ["main-1-1.cpp", "function-1-1.cpp"],
                           provided_files = [], points = 2)
test_compile = CompileTest(submitted_files = ["function-1-1.cpp"],
                           provided_files = ["test-1-1.cpp"], points = 2)
c_tests = [main_compile, test_compile]

# question_id is needed not only for output, but for finding relevant testing files.
# max_points is sum of all marks for this question. This can't be inferred yet without
# searching source/ to see how many tests there are.
q = Question(question_id = "1-1", max_points = 10 compile_tests = c_tests
             file_points = 2, test_points = 2)
"""

# Constants
sub_prefix = "submission/"
src_prefix = "source/"
test_program = "program.out"
program_output = "program.output"
program_error = "program.err"
test_timeout = 5                    # Timeout for all program executions (in seconds)

# ========================================================================
#              Set to true if assignment is a workshop.
# If true, overwrites final score to participation_grade regardless of tests
# for participation grade.
#participation_only = False
#participation_grade = 1
# ========================================================================

# utility functions
def silent_remove(filename):
    try:
        os.remove(filename)
    except OSError:
        pass

# Cleanup temp files
def silent_cleanup():
    silent_remove("program.err")
    silent_remove("program.out")
    silent_remove("program.output")
    silent_remove("testdiff")

# Collection of data for each compiling test
class CompileTest:
    def __init__(self, submitted_files = [], provided_files = [], points = 0):
        self.submitted_files = submitted_files
        self.provided_files = provided_files
        self.points = points

    def get_file_names(self):
        return self.submitted_files + self.provided_files

    def get_file_paths(self):
        ret = []
        for file in self.submitted_files:
            ret.append(sub_prefix + file)
        for file in self.provided_files:
            ret.append(src_prefix + file)
        return ret

# If tester_idx is left as -1, then compiling won't be forced
class Question:
    def __init__(self, question_id, max_points = 0, compile_tests = [], tester_idx = -1,
                 file_points = 0, test_points = 0, extra_files = []):
        self.qid = question_id
        self.max = max_points
        self.f_points = file_points                 # Points given if all req files are present
        self.test_points = test_points              # Points given per correct functionality test

        # List of CompileTest objects, requires at least 1 CompileTest if tests want to be run
        self.compile_tests = compile_tests

        # tester_idx is the index in compile_tests of which compiled program will be
        # used for further testing (and therefore shouldn't be deleted)
        self.tester_idx = tester_idx

        # List of extra files to check for that aren't related to compiling (plan.txt, solution.txt, etc.)
        self.extra_files = extra_files


# Checks if passed file names are present in sub_prefix directory
# Adds score and feedback to current_test
# Returns list of missing file names
def check_present(current_test, file_names = [], max_score = 0):
    # Loop through list of required file names
    # Output names of files it's searching for and search result
    # to use as feedback.
    missing_files = []
    out_str = ""
    for cur_file in file_names:
        cur_path = sub_prefix + cur_file
        file_exists = os.path.isfile(cur_path)

        if file_exists:
            print(f'found: {cur_file}')
            file_size = os.path.getsize(cur_path)
            if file_size == 0:
                out_str += f"Found {cur_file}, but it's empty!\n"
                # Empty files are considered equivalent to the file being missing
                missing_files.append(cur_file)
        else:
            missing_files.append(cur_file)
            out_str += f'File {cur_file} not found!\n'

    score = 0
    if len(missing_files) == 0:
        score = max_score
        out_str += f'All files found, +{max_score} marks.\n'
        print(f'All files found. Required files: {" ".join(file_names)}')
    else:
        print(f'Files missing/empty: {" ".join(missing_files)}')

    current_test["score"] += score
    current_test["output"] += out_str

    return missing_files

# Set current_test to None to not record outcome of compile (used for creating test driver)
def check_compile_target(current_test, points, compile_test):

    file_paths = compile_test.get_file_paths()
    file_names = compile_test.get_file_names()

    out_str = ""

    if current_test == None:
        print("Compiling without recording (for test driver).")

    cmd = ['g++', '-std=c++11', '-o', f'{test_program}', '-O2', '-Wall']
    for path in file_paths:
        cmd.append(path)

    print(f'Compiling {test_program} using files: {" ".join(file_names)}...')
    print(" ".join(cmd))
    compiler_process = subprocess.run(cmd, capture_output=True, text=True, timeout=test_timeout)

    success = False
    if os.path.isfile(f'{test_program}'):
        score = points
        print(f'{test_program} compiled successfully.')
        out_str = f'Successfully compiled {test_program} with files {" ".join(file_names)}. +{points} marks\n'
        success = True
    else:
        score = 0
        print(f'{test_program} failed to compile!')
        print(compiler_process.stdout)
        print(compiler_process.stderr)
        out_str = f'{test_program} failed to compile using files {" ".join(file_paths)}\n'
        out_str += "Compiler stdout:\n"
        out_str += compiler_process.stdout
        out_str += "\n-------\n"
        out_str += "Compiler stderr:\n"
        out_str += compiler_process.stderr
        out_str += "\n-------\n"

    if current_test != None:
        current_test["score"] += score
        current_test["output"] += out_str
    return success

# Assumes I/O is done via files using following format:
#   - Program Args:     args-I-J-XY     [optional]
#   - Input:            input-I-J-XY    [optional]
#   - Expected output:  output-I-J-XY
#   - Test driver:      test-I-J.cpp	[optional]
# Where I-J is question I, subquestion J, XY is two digit test id (e.g. 01)
# Example filenames for questions 3-1 with 2 test cases:
# args-3-1-00, args-3-1-01, input-3-1-00, input-3-1-01, output-3-1-00, output-3-1-01, test-3-1.cpp
# Assumes test ids (XY) is sequential from 00 -> 99. If XY is not found, then test ids > XY are ignored.
def get_test_ids(qid):
    out_name = f'{src_prefix}output-{qid}-'
    test_ids = []
    for X in range(10):
        for Y in range(10):
            cur_id = str(X) + str(Y)
            cur_name = out_name + cur_id
            if os.path.isfile(cur_name):
                test_ids.append(cur_id)
            else:
                # If test id isn't found, stop searching
                return test_ids
    return test_ids

def check_diff(qid, tid):
    # Ensure program output file and expected output file exist
    exp_out_file = f'{src_prefix}output-{qid}-{tid}'
    if not os.path.isfile(exp_out_file):
        err = f"{exp_out_file} doesn't exist. Cannot run diff."
        print(err)
        return err
    if not os.path.isfile("program.output"):
        err = "program.output doesn't exist. Cannot run diff."
        print(err)
        return err

    cmd = ['diff', f'{exp_out_file}', 'program.output']
    diff = subprocess.run(cmd, capture_output=True, text=True, timeout=test_timeout)

    if diff.returncode == 0:
        str_return = ""
    elif diff.returncode == 1:
        str_return = diff.stdout
        str_return += diff.stderr
    else:
        str_return = "Diff encountered an error!\n"
        print(diff.stdout)
        print(diff.stderr)

    print(str_return)
    return str_return

def run_tests(current_test, qid, score_per_test):
    # Get number of tests to run
    test_ids = get_test_ids(qid)

    for tid in test_ids:
        print(f'\nRunning Q{qid}, Test{tid}...')

        # Get program args
        arg_filename = f'{src_prefix}args-{qid}-{tid}'
        program_args = ""

        try:
            with open(arg_filename) as f:
                program_args = f.read().strip()
        except:
            print(f"Couldn't find arg file {arg_filename}")
            pass

        # Get program input
        uses_input = False
        input_filename = f'{src_prefix}input-{qid}-{tid}'
        if os.path.isfile(input_filename):
            uses_input = True

        try:
            if uses_input:
                in_file = open(f'{input_filename}', 'r')
                out_file = open(f'{program_output}', 'w')
                err_file = open(f'{program_error}', 'a')
                prog = subprocess.run([f'./{test_program}', f'{program_args}'],
                                      stdin=in_file, stdout=out_file, stderr=err_file, timeout=test_timeout)
                out_file.flush()
                err_file.flush()
            else:
                out_file = open(f'{program_output}', 'w')
                err_file = open(f'{program_error}', 'a')
                prog = subprocess.run([f'./{test_program}', f'{program_args}'],
                                      stdout=out_file, stderr=err_file, timeout=test_timeout)
                out_file.flush()
                err_file.flush()
        except subprocess.TimeoutExpired:
            feedback = f'Q{qid} Test{tid} program timed out after 5 seconds.'
            current_test["output"] += feedback + "\n"
            print(feedback)
            continue

        # Compare output with output-I-J-{tid}
        feedback = check_diff(qid, tid)

        score = 0
        # A return code of 0 means program terminated successfully w/o issue
        if prog.returncode == 0:
            if len(feedback) != 0:
                print(f'Q{qid}, Test{tid} failed!')
                score = 0
                pre = f'\nQ{qid} Test{tid} failed!\n'
                pre += "\n< EXPECTED-OUTPUT\n---\n> YOUR-OUTPUT\n\n===Begin diff output===\n"
                feedback = pre + feedback
                feedback += "====End diff output====\n"
            else:
                score = score_per_test
                feedback = f'Q{qid} Test{tid} Passed. +{score_per_test} marks\n'
                print(f'Q{qid}, Test{tid} passed.')
        else:
            error_msg = f'Program exit status != 0 (program returned POSIX status code {prog.returncode * -1}): abnormal termination of program (possibly a segmentation fault or timeout).'
            print(error_msg)
            feedback += error_msg + "\n"
            try:
                err_file = open(f'{program_error}', 'r')
                error = err_file.read()
                print(error)
            except:
                print(f'Failed to open {program_error}.')

        current_test["score"] += score
        current_test["output"] += feedback

    silent_cleanup()


def record_test(result_json, test_score, max_score, name, feedback, visibility = "visible"):
    # Create dictionary with test and append to results
    test = {
        "score": test_score,
        "max_score": max_score,
        "name": name,
        "output": feedback,
        "visibility": visibility
    }
    try:
        result_json['tests'].append(test)
    except:
        print("\'tests\' key not found in result_json dictionary")

def apply_cap(meta_test, meta_data, cur_score, participation_only = False, participation_grade = 1):
    max_grade = float(meta_data['assignment']['total_points'])
    capped_score = cur_score

    if cur_score > max_grade:
        meta_test["output"] += f'Capping grade from {cur_score} to {max_grade}\n'
        capped_score = min(cur_score, max_grade)

    if participation_only:
        capped_score = participation_grade
        meta_test["output"] += f'Workshop assessment, +{participation_grade} marks for participation\n'

    return capped_score

def apply_late_penalty(meta_test, meta_data, cur_score):
    score = cur_score

    orig_due_time = datetime.fromisoformat(meta_data['assignment']['due_date'])
    users = meta_data['users']
    latest_due_time = orig_due_time
    for user in users:
        cur_due_time = datetime.fromisoformat(user['assignment']['due_date'])
        if cur_due_time > latest_due_time:
            local_time = cur_due_time.astimezone(timezone('Australia/Adelaide'))
            print(f"Later due time (extension) found for user {user['name']} of {local_time}, instead of original due date: {orig_due_time.astimezone(timezone('Australia/Adelaide'))}")
            latest_due_time = cur_due_time

    sub_time = datetime.fromisoformat(meta_data['created_at'])
    max_grade = float(meta_data['assignment']['total_points'])
    lateness = sub_time - latest_due_time
    if lateness > timedelta(0):
        print(f'Late submission, up to {1+math.ceil(lateness.days)} days late')
        # Cap is 25% per days late
        # cap_percent starts at 0.75 then decreases by 0.25 per FULL day after that
        # This is because if lateness > 0, then submission is "up to" 1 day late
        late_cap_percent = 0.75 - (math.ceil(lateness.days) * 0.25)
        late_capped_score = max_grade*late_cap_percent
        new_score = min(cur_score, late_capped_score)
        meta_test["output"] += "Late submission, "
        meta_test["output"] += f'max available marks capped to {late_cap_percent*100}%.\n'
        meta_test["output"] += f'Original grade of {cur_score} '
        if new_score < cur_score:
            meta_test["output"] += f'capped to {new_score}.\n'
        else:
            meta_test["output"] += "unchanged.\n"
        score = new_score
    return score

def check_previous(meta_test, meta_data, cur_score):
    # Check previous submissions and use highest grade
    prev_subs = meta_data["previous_submissions"]
    best_score = cur_score
    best_date = ""
    for sub in prev_subs:
        sub_score = float(sub["score"])
        if sub_score > best_score:
            best_score = sub_score
            best_date = sub["submission_time"]

    # If better score found, best_date will contain time of submission
    if best_date != "":
        sub_time = datetime.fromisoformat(best_date)
        local_time = sub_time.astimezone(timezone('Australia/Adelaide'))
        print(f'Better submission found with grade: {best_score}')
        print(f'Better submission from time: {local_time} (Adelaide time)')
        meta_test["output"] += f'Better submission found with grade: {best_score}.\n'
        meta_test["output"] += f'Better submission from time: {best_date} (Adelaide time)\n'
    return best_score

def run_questions(questions, participation_only = False, participation_grade = 1):
    meta_data = {}
    try:
        md = open('submission_metadata.json')
        meta_data = json.load(md)
    except BaseException as ex:
        print(f'An error occured when trying to open submission_metadata.json')
        print(str(ex))

    result_json = {'score': 0, 'visibility': 'visible', 'stdout_visibility': 'hidden', 'tests': []}

    # ===============================
    #       Run Question tests
    # ===============================
    for q in questions:
        silent_remove(f'{test_program}')

        qid = q.qid

        req_file_names = set()
        for test in q.compile_tests:
            for cur_file in test.submitted_files:
                req_file_names.add(cur_file)

        for cur_file in q.extra_files:
            req_file_names.add(cur_file)
        f_points = q.f_points

        # Of the required files, move any header files from submission to source to ensure test drivers can compile
        for cur_file in req_file_names:
            components = cur_file.split('.')
            ext = components[-1]

            try:
                if ext == "h" or ext == 'hpp':
                    print(f'\n========= Header file required: {cur_file}')
                    # Don't overwrite file if it exists
                    if not os.path.isfile(src_prefix + cur_file):
                        print(f'Attempting to move {sub_prefix + cur_file} to {src_prefix + cur_file} to ensure test drivers can compile.')
                        shutil.copyfile(sub_prefix + cur_file, src_prefix + cur_file)
                    else:
                        print(f'{src_prefix + cur_file} already exists. Not moving as it will overwrite existing file.')
            except BaseException as ex:
                print(f'An error occured when trying to move required files.')
                print(str(ex))
                continue

        current_test = {
            "score": 0,
            "max_score": 0,
            "name": f'Q{qid}',
            "output": ""
        }

        print(f'\n==================')
        print(f'      Q{qid}      ')
        print(f'==================')

        # If failed, skip question because won't compile
        missing_files = check_present(current_test, list(req_file_names), f_points)

        compiled = False
        for compile_test in q.compile_tests:
            compiled = check_compile_target(current_test, compile_test.points, compile_test)
            silent_remove(f'{test_program}')


        # Separately compile test driver
        if len(q.compile_tests) != 0:
            idx = q.tester_idx
            compiled = check_compile_target(None, 0, q.compile_tests[idx])

        # If test driver didn't successfully compile, don't run tests
        if not compiled:
            print()
            print(f'Q{qid} functionality tests skipped due to test driver failing to compile.')
            print()
            record_test(result_json, current_test["score"], q.max, current_test["name"], current_test["output"])
            continue

        # Run tests
        run_tests(current_test, qid, q.test_points)

        record_test(result_json, current_test["score"], q.max, current_test["name"], current_test["output"])

        sys.stdout.flush()

    # ===============================
    #      Capping/Late Penalties
    # ===============================

    # Add test to results that gives no grades but provides details on submission,
    # such as whether grade exceeds cap/max available marks, late penalties, whether previous
    # submission grades are used, etc.
    meta_test = {
        "score": 0,
        "max_score": 0,
        "name": "Submission details",
        "output": ""
    }

    # Calculate total score as sum of all test scores
    total_score = 0
    for test in result_json['tests']:
        total_score += test['score']

    total_score = apply_cap(meta_test, meta_data, total_score, participation_only, participation_grade)

    total_score = apply_late_penalty(meta_test, meta_data, total_score)

    total_score = check_previous(meta_test, meta_data, total_score)

    result_json['tests'].append(meta_test)
    result_json['score'] = total_score

    return result_json


if __name__ == "__main__":
    print("Incorrectly running utility function as main driver. Run run_autograder instead.")