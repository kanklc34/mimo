# Mimo Kurye project instructions

- Follow test-first development: add or update tests before implementation.
- Run the relevant tests after every implementation step with `C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest ...`.
- Do not use `pip.exe`, `venv`, or another Python interpreter. Use `C:\Users\KAAN\miniconda3\envs\mimo\python.exe` for every Python command, including pytest.
- Keep code organized in `models/`, `constraints/`, `generator/`, `solver/`, `validator/`, and `api/` modules.
- The `solver` and `validator` modules must never import each other; each may import only `models` and `constraints` from this project.
- Represent every time as an integer number of minutes since the courier shift starts.
- Make small, meaningful commits. Run tests at each step.
- No OR-Tools solver, Gemini integration, or user interface is in scope yet.
