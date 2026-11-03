# One-Change-at-a-Time Rule

This rule governs how you present multi-item work of **any** kind. It applies to: reviewer comments; manuscript edits; code changes; items on a to-do list; sub-tasks that together complete a larger task; and **every question the user must answer** — whether to clarify next steps, approve a change, choose between options, or make a decision. Present exactly **ONE** such item at a time, then stop and wait.

## The rule

- Present **one item** per message — one comment, one edit, one task, one sub-task, one question, one decision, one option-set to choose from. Never bundle multiple items into a single message, and **never present a long list and then ask for agreement in one bulk prompt at the end.**
- After presenting it, **stop and wait** for the user's response (applying it, "next", an answer, or feedback) before presenting the next item.
- This holds even when items look related: if a reviewer comment has a response block plus several edits, present the response, then each edit, one message at a time.
- **Pre-approval is NOT permission to batch.** "I approve all changes", "approved", "go ahead with all of them", or any blanket sign-off means the *direction* is agreed. It does **not** mean dump everything into one message, and it does **not** mean auto-advance through items.
- Plural phrasing ("give me the prompts", "the edits", "the comments") is **not** a batch request. Only batch when the user explicitly says "all in one message" / "give me the whole set at once". When in doubt, present one and wait.

## Word manuscript-edit prompts

When the user asks for a prompt to drive a manuscript edit in Word (a "Claude in Word" prompt), the prompt text must:

1. **Instruct Claude-in-Word to propose the change as a reviewable edit card first** — present the exact before/after (text to REMOVE and text to ADD) and **wait for the user's approval before changing the document.** Do not have it apply the edit outright.
2. **State that the user approves the change before it is applied:** turn on Track Changes, and once approved apply the change as a tracked change the user still reviews and accepts — nothing auto-accepted.

Every such prompt must carry both instructions.

**Why:** the user applies and reviews each change before the next.

Background and examples: docs/rules-history.md.
