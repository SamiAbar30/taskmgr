# TaskMgr: Command-Line Task Manager

**Group 15 - Software Verification and Validation Assignment**
**Members:** ABAR SAMI, JIN RONGHAO, SAEED FAHAD

## Description
taskmgr is a command-line application designed to manage tasks by processing sequential commands from text files. This project includes the source code, the executable, and the test suite used to achieve 100% Branch Coverage as part of the White-box testing assignment.

## Repository Content

* **taskmgr.py**: The final Python source code, patched to achieve 100% coverage.
* **taskmgr_initial_version.py**: The original source code before error patching.
* **taskmgr.exe**: The standalone executable version (compiled with PyInstaller).
* **test04.txt**: The final comprehensive test suite that includes all functional paths and error handling (Iteration #4).
* **test01.txt - test03.txt**: Test cases from previous iterations.

---

## Execution Instructions

You can run the application using the standalone executable or the Python script.

### 1. Using the Executable (Recommended)
No Python installation is needed. Open your terminal in the project folder and run:

    taskmgr.exe test04.txt

### 2. Using Python
If you prefer running the source code directly:

    python taskmgr.py test04.txt

---

## How to Check Coverage (100%)

To reproduce the White-Box testing results and verify the 100% branch coverage, you need the coverage library installed (pip install coverage).

Run the following commands in the command line in this specific order to cover the main logic and the edge cases (file not found & usage errors):

1. Reset previous data:
   py -m coverage erase

2. Run the main test suite (Happy Path + Errors):
   py -m coverage run --branch taskmgr.py test04.txt

3. Run edge case: File does not exist:
   py -m coverage run --branch -a taskmgr.py testNoExist.txt

4. Run edge case: No arguments provided:
   py -m coverage run --branch -a taskmgr.py

5. Generate the HTML Report:
   py -m coverage html

After running step 5, open the generated htmlcov/index.html file in your browser to see the green 100% coverage report.

Here is a code snippet you can use to reach 100% coverage:

    py -m coverage erase
    py -m coverage run --branch taskmgr.py test04.txt
    py -m coverage run --branch -a taskmgr.py testNoExist.txt
    py -m coverage run --branch -a taskmgr.py
    py -m coverage html

---

## Re-building the Executable (Optional)

If you modify taskmgr.py and want to regenerate the .exe, use PyInstaller:

    pip install pyinstaller
    py -m PyInstaller -F -n taskmgr taskmgr.py

The new executable will be placed in the dist folder.