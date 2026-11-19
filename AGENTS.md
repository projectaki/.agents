# Instructions

My rules live in the amx plugin, which is installed in this harness. Its skills run as `amx:<name>`. This file only points to them. Do not add rules here.

- Before you make a design or code decision, load the `amx:brain` skill. Then read each principle file in it whose condition applies.
- Read the agent references in the `references/` folder of the `amx:go` skill when their condition applies:
  - `approval-for-exceptions.md`: read before you deviate from a standard, use a temporary workaround, or build on an uncertain design.
  - `file-search.md`: read before you search files in a git repository.
