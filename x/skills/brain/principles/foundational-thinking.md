# Foundational Thinking

Structural decisions keep future options open. Code-level decisions keep the code simple.

## Data structures first

Get the data shape right before you write logic. Define the core types early. Trace every path that reads or writes the data. Choose structures that fit the most common paths.

## Remove duplicate structure, not every duplicate line

Types and data models must not repeat. Repeated statements are acceptable. Three similar statements are better than an abstraction that you create too early. Prefer explicit code to clever code.

## Scaffold first

If something helps every later phase, build it first. Ask: "Does every later phase benefit when this exists?" CI, linting, test infrastructure, and shared types are scaffold. Do setup before features. Write tests before fixes. Keep commits small, with one purpose each.

## One clear abstraction per step

Each step adds one clear abstraction or improves one that exists. Do not spread a new capability across callers as special cases.
