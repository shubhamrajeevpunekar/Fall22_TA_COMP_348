import os
import glob
import shutil
from zipfile import ZipFile
import pandas as pd
from typing import List
import logging

logging.basicConfig(level=logging.INFO)

ASSIGNMENT_ROOT = "/mnt/d/TA/COMP 348/Grading/GRADING/A01"
STUDENT_CSV = "/mnt/d/TA/COMP 348/Grading/GRADING/students.csv"
FILTERED_ASSIGNMENT_ROOT = "/".join(ASSIGNMENT_ROOT.split("/")[:-1] + ["A01_filtered"])

def filter_submissions(df_students, assignment_paths):
    def filter_students(assignment_path):
        # ~30x30, brute force should be fine for now
        for i in range(len(df_students)):
            if df_students.first_name[i] in assignment_path and df_students.last_name[i] in assignment_path:
                return True
        # print("Submission missing: " + assignment_path)
        return False

    return list(filter(filter_students, assignment_paths))


def check_submissions(df_students: pd.DataFrame, filtered_assignment_paths: List[str]):
    # return student who has an entry in df, but no assignment path
    for student in df_students.iterrows():
        found = False
        for filtered_assignment_path in filtered_assignment_paths:
            if student[1].first_name in filtered_assignment_path and student[1].last_name in filtered_assignment_path:
                found = True
                break
        if not found:
            logging.warning(f"{student[1].id} -> {student[1].first_name} {student[1].last_name}")


def copy_assignments(destination_path, filtered_assignment_paths):
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)

    new_paths = []
    for filtered_assignment_path in filtered_assignment_paths:
        new_path = os.path.join(destination_path, filtered_assignment_path.split("/")[-1])
        shutil.copytree(filtered_assignment_path, new_path)
        new_paths.append(new_path)
    return new_paths

def unzip_submissions(filtered_assignments_root):
    for subdir, dirs, files in os.walk(filtered_assignments_root):
        for file in files:
            full_name = os.path.join(subdir, file)
            if full_name.endswith(".zip"):
                with ZipFile(full_name, 'r') as zipObj:
                    # Extract all the contents of zip file in different directory
                    zipObj.extractall(subdir)


def main():
    assignment_paths = glob.glob(os.path.join(ASSIGNMENT_ROOT, "*"))
    logging.info(f"Found {len(assignment_paths)} submissions")

    df_students = pd.read_csv(STUDENT_CSV)
    logging.info(f"Assigned {len(df_students)} students for grading")

    filtered_assignment_paths = filter_submissions(df_students, assignment_paths)
    logging.info(f"Filtered submissions based on assigned students: {len(filtered_assignment_paths)} submissions")

    logging.info(f"Missing submissions for following students: ")
    check_submissions(df_students, filtered_assignment_paths)

    moved_assignment_paths = copy_assignments(FILTERED_ASSIGNMENT_ROOT, filtered_assignment_paths)
    logging.info(f"Moving submissions to {FILTERED_ASSIGNMENT_ROOT}: {len(moved_assignment_paths)}")

    # Check the filtered submissions folder with the df
    grading_submissions_paths = glob.glob(os.path.join(FILTERED_ASSIGNMENT_ROOT, "*"))
    logging.info(f"Submissions for grading in {FILTERED_ASSIGNMENT_ROOT}: {len(grading_submissions_paths)}")
    logging.warning(f"Missing students for grading (CHECK ON MOODLE) ::: ")
    check_submissions(df_students, grading_submissions_paths)

    # Unzip submissions
    unzip_submissions(FILTERED_ASSIGNMENT_ROOT)
    logging.info(f"Unzipped submissions in {FILTERED_ASSIGNMENT_ROOT}")

if __name__ == "__main__":
    main()
