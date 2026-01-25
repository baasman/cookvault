### RULES

* At the start of a new session, check if `.implementation-history/active-plan.md` exists. If so, read it and inform the user about the in-progress implementation plan.

* **MANDATORY:** Immediately after a plan is approved (ExitPlanMode is accepted by the user), invoke the `plan-history` skill to create `.implementation-history/active-plan.md`. Do NOT proceed with implementation until this is done.

* When running a script, always use the interpreter from the virtual environment, location in .venv/

* When catching exceptions in python code, always ensure that the original error is logged, and the traceback is printed out

* If an exception is caught and being logged, make sure it's clear where the error occurred in the code

* ALWAYS use uv when running python based commands

* Imports should always be at the top level

* The only important .env file is the one in the root directory