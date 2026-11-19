# Framework and Feature Boundaries

Framework code never names or imports a specific feature.

When behavior differs by kind, the framework defines an interface.
Each feature implements that interface next to its own code.
Register each implementation with a key outside the framework.
The framework uses that key to find the implementation.

Adding a new kind requires new feature files and one registration line.
It must not require changes to framework logic.
Do not add branches in framework code for specific features or kinds.

Apply this pattern where behavior must vary.
Do not add interfaces for hypothetical variation.
