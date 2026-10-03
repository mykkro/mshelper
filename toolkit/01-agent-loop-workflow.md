# The Manual Agent Loop

Agent-mode tools work well because they loop: **plan → act → observe → adjust**. With Copilot chat,
you run the "act" and "observe" parts. This file gives you prompts for each stage.

```text
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. Brief │ →  │ 2. Plan  │ →  │ 3. One step  │ →  │ 4. You run   │
└──────────┘    └──────────┘    └──────────────┘    │ tests/linter │
                                      ↑             └──────┬───────┘
                                      └──── 5. Paste output ┘
                                   (when the chat gets long → 6. Handoff)
```

---

## 1. Brief: describe the task

```text
TASK
{{What you want, in plain words. Describe the outcome, not the implementation.}}

ACCEPTANCE CRITERIA
- {{observable behavior 1}}
- {{observable behavior 2}}
- Existing tests still pass.

RELEVANT CODE
{{paste files / functions — see 02-context-packing.md}}

OUT OF SCOPE
- {{things that must NOT change}}

Do not write code yet. First restate the task, list your assumptions, and ask any questions you need answered.
```

## 2. Plan: get a reviewable plan

```text
Now propose an implementation plan:
- Numbered steps, each small enough to finish and verify in one reply.
- For each step: the files touched, what changes, and how I verify it (command + expected result).
- Mark any step that is risky or that you are unsure about.
- Put tests first where practical.
Do not write code yet. Wait for my "go".
```

Review the plan. Push back on it. It is much cheaper to fix the plan than to fix the code later.

## 3. Execute one step

```text
Go: step {{N}}. Give only the changes for this step, in the agreed format, then the verify command.
```

To speed up once you trust the plan:

```text
Do steps {{N}} to {{M}} in one reply. Stop early if something is uncertain.
```

## 4–5. Feed back reality

After you apply the change and run the command, paste the result:

````text
Applied step {{N}}. Ran `{{command}}`. Output:
```
{{paste the full output, or the relevant part plus ~20 lines around the error}}
```
{{optional: what you observed / anything you changed by hand}}
Continue: if it's green, go to the next step. If it's red, diagnose before you fix.
````

If Copilot keeps going in circles (the same fix twice, or flip-flopping):

```text
Stop. We have tried {{X}} and {{Y}} and both failed. Don't propose another fix yet.
List the 3 most likely root causes, ranked, with the evidence for each, and tell me which single
diagnostic (a print/log/command) would tell them apart.
```

## 6. Handoff: move to a fresh chat

Long chats lose earlier context without warning. When quality drops, or every ~15–20 messages:

```text
Write a HANDOFF NOTE that I will paste into a new chat. Include:
1. Goal and acceptance criteria.
2. Plan with each step's status (done / in progress / todo).
3. Key decisions made and why.
4. Current state of each touched file (only the changed parts, or full code for small files).
5. Open problems and the last error output.
6. The exact next step.
Be complete but terse. The new chat will have no other context.
```

In the new chat, paste the **session primer**, then the handoff note, then: `Continue from the next step.`

---

## Final review before commit

```text
We are done implementing. Review the full set of changes as a strict code reviewer:
- Bugs, unhandled edge cases, error-handling gaps
- Anything that doesn't meet the acceptance criteria
- Leftover debug code, TODOs, dead code, inconsistent naming
- Missing tests
List the issues by severity (blocker / should-fix / nit). Don't rewrite the code unless I ask.
```

Then:

```text
Write a git commit message: an imperative subject line of 72 chars or less, a blank line, then a body
explaining what changed and why (wrap at 72). Mention any breaking changes.
```
