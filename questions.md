- Q: Why the difference between esr and esr-sysaddon channels? Can we combine?
  - A: -sysaddon is the test channel

- Q: If I have a mapping of `channel-version` to `blobs`, in theory I can make sure the `blobs` are populated in a superblob, and make sure that we map the correct superblob to an appropriate rule. However, how do I tell if there's already a rule? How should I lay out and adjust priorities?
  - For the rule, I might be able to look for another rule with the same version?
  - At most we have 69 rules in a single channel, so adjusting priorities should hopefully be ok
  - This is probably easier to do if we have version globs, e.g. `version: 68.*` or `version: 68.1.*` rather than having to rely on `version: <69` or `version: <68.2.0`. Can/should I help here?
  - What about special rules? Do we need to support them?
  - I imagine we can completely refactor the -sysaddon channel(s) and make sure they look the way we want before we refactor the prod channel(s)
