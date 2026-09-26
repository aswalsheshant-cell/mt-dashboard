# Merge preview template

Produce this, then stop. The owner approves one merge per approval.

```
ACTION PREVIEW — PR #<n>: <title>
Action requested: squash-merge #<n> into main            (nothing else)

State (fresh, <time>)
  main           <sha>
  PR head        <sha>        merge base <sha | none>
  Mergeable      yes/no       up to date with main: yes/no
  Required checks  6/6 green on head <sha>   (list any non-green with its label)
  Other workflows touched by the PR: <name> — <conclusion>, log read: yes

Scope          <n> files: <list>
Not changed    data.js, config/, PowerBI/, seed data, baselines   (<diff command>)

Findings
  <class> / <severity> / <status> — <one line> — <evidence>
  (or: none open)

Proof
  Fails before fix: <test> on <main sha>: <result>
  Passes after:     <test> on <head sha>: <result>
  Wider suites:     <command>: <result>

Owner decisions needed
  1. <decision> — options and recommendation
Follow-ups recorded (not in this PR)
  - <item> — <where recorded>

After merge (by change-verification)
  confirm merged tree == tested head; post-merge CI; update the next PR from main
```
